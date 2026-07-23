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

module "aci" {
  source = "netascode/nac-aci/aci"
  # version = "1.2.0"
  version = ">=2.0.0"

  # source = "github.com/netascode/terraform-aci-nac-aci?ref=main"

  yaml_files = ["data/csr-l3out.nac.yaml"]

  manage_access_policies    = false
  manage_fabric_policies    = false
  manage_pod_policies       = false
  manage_node_policies      = false
  manage_interface_policies = false
  manage_tenants            = true
}
