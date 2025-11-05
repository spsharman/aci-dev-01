terraform {
  required_providers {
    aci = {
      source = "CiscoDevNet/aci"
      # version = ">=2.13.2"
    }
  }
}

provider "aci" {
  username = var.apic_username
  password = var.apic_password
  url      = var.apic_url
}

module "aci" {
  source  = "netascode/nac-aci/aci"
  # version = ">=0.8.1"

# Floating SVI configuration

  yaml_files = ["data/configuration-v1.nac.yaml"]


  manage_access_policies    = false
  manage_fabric_policies    = false
  manage_pod_policies       = false
  manage_node_policies      = false
  manage_interface_policies = false
  manage_tenants            = true
}