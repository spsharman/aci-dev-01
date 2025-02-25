# Need to modify .terraform/modules/aci/defaults/defaults.yaml 
# Set apic/fabric_policies/global_settings/overlapping_vlan_validation: false
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

  yaml_directories = ["data", "data/git-ignored"]

  manage_access_policies    = false
  manage_fabric_policies    = true
  manage_pod_policies       = false
  manage_node_policies      = false
  manage_interface_policies = false
  manage_tenants            = false
}
