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

  # yaml_directories = ["data"] # to exclude a set of configuration move the .nac.yaml file to the /data/excluded directory

  # yaml_files = ["1-base-build.nac.yaml"]
  # yaml_files = ["2-secure-application-staging.nac.yaml"]
  yaml_files = ["3-application-esgs.nac.yaml"]
  # yaml_files = ["4-vzany-for-intra-vrf.nac.yaml"]
  # yaml_files = ["5-preferred-group.nac.yaml"]


  # yaml_files = ["data/blueprints/blueprint-1.nac.yaml"]
  # yaml_files = ["data/blueprints/blueprint-2.nac.yaml"]
  # yaml_files = ["data/blueprints/blueprint-3.nac.yaml"]
  # yaml_files = ["data/blueprints/blueprint-4.nac.yaml"]
  # yaml_files = ["data/blueprints/blueprint-5.nac.yaml"]
  # yaml_files = ["data/blueprints/blueprint-6.nac.yaml"]
  # yaml_files = ["data/blueprints/blueprint-7.nac.yaml"]
  # yaml_files = ["data/blueprints/blueprint-8.nac.yaml"]
  # yaml_files = ["data/blueprints/blueprint-9.nac.yaml"]
  # yaml_files = ["data/blueprints/blueprint-10.nac.yaml"]

  manage_access_policies    = false
  manage_fabric_policies    = false
  manage_pod_policies       = false
  manage_node_policies      = false
  manage_interface_policies = false
  manage_tenants            = true
}
