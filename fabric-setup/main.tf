terraform {
  required_providers {
    aci = {
      source = "CiscoDevNet/aci"
      version = ">=2.13.2"
    }
  }
}

provider "aci" {
  username = var.apic_username
  password = var.apic_password
  url      = var.apic_url
}

module "aci" {
    # source = "github.com/netascode/terraform-aci-nac-aci?ref=main"
  source  = "netascode/nac-aci/aci"
  version = ">=0.8.1"

  # yaml_directories = ["data"]
  yaml_files = [
    "data/system-settings.nac.yaml",
    "data/fabric-policies.nac.yaml",
    "data/admin-settings.nac.yaml",
    "data/virtual-networking.nac.yaml"
    ]


  manage_access_policies    = false
  manage_fabric_policies    = true
  manage_pod_policies       = false
  manage_node_policies      = false
  manage_interface_policies = false
  manage_tenants            = false
}
