terraform {
  required_providers {
    aci = {
      source = "CiscoDevNet/aci"
    }
  }
}

provider "aci" {
  username = var.apic_username
  password = var.apic_password
  url      = var.apic_url
}

# Source of truth: derive set rules directly from NAC YAML.
locals {
  nac_config           = yamldecode(file(var.nac_yaml_file))
  selected_tenant      = one([for tenant in local.nac_config.apic.tenants : tenant if tenant.name == var.tenant_name])
  selected_app_profile = one([for ap in try(local.selected_tenant.application_profiles, []) : ap if ap.name == var.application_profile_name])
  selected_esgs        = try(local.selected_app_profile.endpoint_security_groups, [])
  discovered_esg_names = [for esg in local.selected_esgs : esg.name]
  managed_esg_names    = [for name in local.discovered_esg_names : name if !contains(var.exclude_esg_names, name)]
  generated_set_rule_data = {
    for esg_name in local.managed_esg_names : esg_name => {
      tenant_name              = var.tenant_name
      application_name         = esg_name
      application_profile_name = var.application_profile_name
      esg_name                 = esg_name
    }
  }
}

# 1) Parent policy object:
#    Creates one rtctrlAttrP per ESG discovered from the NAC YAML profile.
resource "aci_rest_managed" "set_rule_policy" {
  for_each   = local.generated_set_rule_data
  dn         = "uni/tn-${each.value.tenant_name}/attr-${each.value.application_name}"
  class_name = "rtctrlAttrP"

  content = {
    name      = each.value.application_name
    descr     = ""
    nameAlias = ""
  }

  child {
    rn         = "sptag"
    class_name = "rtctrlSetPolicyTag"
    content = {
      name      = ""
      descr     = ""
      nameAlias = ""
      type      = "policy-tag"
    }
  }
}

# 2) Relationship object:
#    Links each generated set-rule policy to the corresponding ESG.
resource "aci_rest_managed" "set_policy_tag_to_esg" {
  for_each   = local.generated_set_rule_data
  dn         = "${aci_rest_managed.set_rule_policy[each.key].id}/sptag/rssetPolicyTagToESg"
  class_name = "rtctrlRsSetPolicyTagToESg"

  content = {
    tDn = "uni/tn-${each.value.tenant_name}/ap-${each.value.application_profile_name}/esg-${each.value.esg_name}"
  }

  depends_on = [aci_rest_managed.set_rule_policy]
}
