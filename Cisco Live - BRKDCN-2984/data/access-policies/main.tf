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

  yaml_directories = ["configuration-files-old-model"] # to exclude a set of configuration move the .nac.yaml file to the /data/excluded directory
  # yaml_directories = ["configuration-files-new-model"] # to exclude a set of configuration move the .nac.yaml file to the /data/excluded directory

  manage_access_policies    = true
  manage_fabric_policies    = false
  manage_pod_policies       = false
  manage_node_policies      = false
  manage_interface_policies = true
  manage_tenants            = false
}
