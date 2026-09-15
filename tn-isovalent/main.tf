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

# Floating SVI configuration

  # yaml_files = ["floating-svi/configuration-v1.nac.yaml"]
  # yaml_files = ["floating-svi/configuration-v2.nac.yaml"]
  # yaml_files = ["floating-svi/configuration-v3.nac.yaml"]
  # yaml_files = ["floating-svi/configuration-v4.nac.yaml"]
  # yaml_files = ["floating-svi/configuration-v5.nac.yaml"]
  # yaml_files = ["floating-svi/configuration-v6.nac.yaml"]
  # yaml_files = ["floating-svi/configuration-v7.nac.yaml"]
  # yaml_files = ["floating-svi/configuration-v8.nac.yaml"] << working configuration
  # yaml_files = ["floating-svi/configuration-v9.nac.yaml"]
  yaml_files = ["floating-svi/configuration-v10.nac.yaml"] # << testing Smart Switch iBGP AS65151


# SVI configuration

  # yaml_files = ["svi/configuration.nac.yaml"]

  manage_access_policies    = false
  manage_fabric_policies    = false
  manage_pod_policies       = false
  manage_node_policies      = false
  manage_interface_policies = false
  manage_tenants            = true
}