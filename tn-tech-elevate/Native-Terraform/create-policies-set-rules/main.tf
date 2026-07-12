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

# 1) Parent policy object:
#    Creates one rtctrlAttrP per set rule.
resource "aci_rest_managed" "set_rule_policy" {
  for_each   = var.set_rules
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
#    For each set rule, links policy-tag to the target ESG.
resource "aci_rest_managed" "set_policy_tag_to_esg" {
  for_each   = var.set_rules
  dn         = "${aci_rest_managed.set_rule_policy[each.key].id}/sptag/rssetPolicyTagToESg"
  class_name = "rtctrlRsSetPolicyTagToESg"

  content = {
    tDn = "uni/tn-${each.value.tenant_name}/ap-${each.value.application_profile_name}/esg-${each.value.esg_name}"
  }

  depends_on = [aci_rest_managed.set_rule_policy]
}
