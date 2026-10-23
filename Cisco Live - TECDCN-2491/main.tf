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
  source  = "netascode/nac-aci/aci"
  version = "2.1.0"

  # yaml_directories = ["data"] # to exclude a set of configuration move the .nac.yaml file to the /data/excluded directory

  yaml_files = ["data/configuration-v1.nac.yaml"]
  # yaml_files = ["data/configuration-v2.nac.yaml"]

  manage_access_policies    = false
  manage_fabric_policies    = false
  manage_pod_policies       = false
  manage_node_policies      = false
  manage_interface_policies = false
  manage_tenants            = true
}
