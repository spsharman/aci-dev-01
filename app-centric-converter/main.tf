terraform {
  required_providers {
    aci = {
      source  = "CiscoDevNet/aci"
      version = ">= 2.0.0"
    }
  }
}

provider "aci" {
  username = var.apic_username
  password = var.apic_password
  url      = var.apic_url
}

#############################################
# Load CSV and build mappings
#############################################

locals {
  # Load CSV rows into objects
  app_rows = csvdecode(file(var.application_details_file))

  # Extract list of IPs
  ips = [for row in local.app_rows : row.ip_address]

  # Extract unique application names
  applications = distinct([for row in local.app_rows : row.application_name])

  # Map application → tenant (first matching row)
  app_profiles = {
    for app in local.applications :
    app => (
      [for row in local.app_rows : row.tenant if row.application_name == app][0]
    )
  }

  # Map application → isolated mode (string)
  isolated_map = {
    for app in local.applications :
    app => (
      [for row in local.app_rows : lower(row.isolated) if row.application_name == app && row.isolated != ""][0]
      != "" ?
      [for row in local.app_rows : lower(row.isolated) if row.application_name == app && row.isolated != ""][0] :
      lower(var.isolated)
    )
  }

  # Map application → preferred-group mode (string)
  preferred_group_map = {
    for app in local.applications :
    app => (
      [for row in local.app_rows : lower(row["preferred-group"]) if row.application_name == app && row["preferred-group"] != ""][0]
      != "" ?
      [for row in local.app_rows : lower(row["preferred-group"]) if row.application_name == app && row["preferred-group"] != ""][0] :
      lower(var.preferred_group)
    )
  }

  # Map application → VRF name (from first matching IP)
  vrf_map = {
    for app in local.applications :
    app => (
      # find first IP for this application
      local.mac_bd_mapping[
        [for row in local.app_rows : row.ip_address if row.application_name == app][0]
      ].vrf_name
    )
  }

  # Map IP → application name
  ip_application_map = {
    for row in local.app_rows :
    row.ip_address => row.application_name
  }
}


#############################################
# fvIp lookup (IP → MAC)
#############################################

data "aci_rest" "ip_lookup" {
  for_each = toset(local.ips)

  path = "/api/node/class/fvIp.json?query-target=subtree&query-target-filter=eq(fvIp.addr,\"${each.key}\")"
}

#############################################
# MAC extraction
#############################################

locals {
  macs = {
    for ip in local.ips :
    ip => try(
      (
        length(regexall(
          "cep-([^/]+)",
          join(" ", values(data.aci_rest.ip_lookup[ip].content))
        )) > 0
          ? regexall("cep-([^/]+)", join(" ", values(data.aci_rest.ip_lookup[ip].content)))[0][0]
          : "IP ${ip} doesn't exist"
      ),
      "IP ${ip} not found (query failed)"
    )
  }

  valid_macs = {
    for ip, mac in local.macs :
    ip => mac
    if !startswith(mac, "IP ")
  }
}

#############################################
# fvCEp lookup (MAC → BD)
#############################################

data "aci_rest" "cep_lookup" {
  for_each = local.valid_macs

  path = "/api/node/class/fvCEp.json?query-target-filter=eq(fvCEp.mac,\"${each.value}\")"
}

#############################################
# BD + VRF extraction
#############################################

locals {
  mac_bd_mapping = {
    for ip, mac in local.valid_macs :
    ip => {
      mac   = mac
      bd_dn = try(data.aci_rest.cep_lookup[ip].content["bdDn"], "")
      bd_name = try(
        data.aci_rest.cep_lookup[ip].content["bdDn"] != "" &&
        length(regexall("BD-([^/]+)", data.aci_rest.cep_lookup[ip].content["bdDn"])) > 0
          ? regexall("BD-([^/]+)", data.aci_rest.cep_lookup[ip].content["bdDn"])[0][0]
          : "No BD",
        "No BD"
      )

      # NEW: Extract VRF DN
      vrf_dn = try(data.aci_rest.cep_lookup[ip].content["vrfDn"], "")

      # NEW: Extract VRF name (after ctx-)
      vrf_name = try(
        length(regexall("ctx-([^/]+)", data.aci_rest.cep_lookup[ip].content["vrfDn"])) > 0
          ? regexall("ctx-([^/]+)", data.aci_rest.cep_lookup[ip].content["vrfDn"])[0][0]
          : "unknown-vrf",
        "unknown-vrf"
      )
    }
  }
}


#############################################
# Tenant lookup (all rows use same tenant)
#############################################

data "aci_tenant" "name" {
  name = local.app_rows[0].tenant
}

#############################################
# Create MAC tags
#############################################

resource "aci_endpoint_tag_mac" "tenant" {
  for_each = local.mac_bd_mapping

  depends_on = [
    data.aci_rest.ip_lookup,
    data.aci_rest.cep_lookup
  ]

  parent_dn = data.aci_tenant.name.id
  bd_name   = each.value.bd_name
  mac       = each.value.mac

  tags = [
    {
      key   = var.app_tag_key
      value = local.ip_application_map[each.key]
    }
  ]
}

#############################################
# Create Application Profiles
#############################################

resource "aci_application_profile" "app" {
  for_each = local.app_profiles

  depends_on = [
    aci_endpoint_tag_mac.tenant
  ]

  parent_dn = "uni/tn-${each.value}"
  name      = each.key
}

#############################################
# Create ESGs inside each Application Profile
#############################################

resource "aci_endpoint_security_group" "esg" {
  for_each = local.app_profiles

  depends_on = [
    aci_application_profile.app
  ]

  parent_dn = "uni/tn-${each.value}/ap-${each.key}"
  name      = "${each.key}-all-endpoints"

  relation_to_vrf = {
    vrf_name = local.vrf_map[each.key]
  }

  intra_esg_isolation     = local.isolated_map[each.key]
  preferred_group_member  = local.preferred_group_map[each.key]
}

#############################################
# Add tag selector to each ESG
#############################################

resource "aci_endpoint_security_group_tag_selector" "esg_tag" {
  for_each = local.app_profiles

  depends_on = [
    aci_endpoint_security_group.esg
  ]

  endpoint_security_group_dn = aci_endpoint_security_group.esg[each.key].id

  match_key   = var.app_tag_key   # e.g. "application-name"
  match_value = each.key          # application_name from CSV
}

#############################################
# Outputs
#############################################

output "ip_mac_bd_mapping" {
  value = local.mac_bd_mapping
}

output "summary" {
  value = [
    for ip, info in local.mac_bd_mapping :
    "${ip} | ${info.mac} | ${local.ip_application_map[ip]} | ${local.app_profiles[local.ip_application_map[ip]]} | ${info.vrf_name} | ${info.bd_name} | ${local.ip_application_map[ip]} | ${local.ip_application_map[ip]}-all-endpoints"
  ]
}

