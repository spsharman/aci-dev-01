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
  # source  = "netascode/nac-aci/aci"
  source = "git::https://github.com/netascode/terraform-aci-nac-aci?ref=main"

  # yaml_directories = ["data"] # to exclude a set of configuration move the .nac.yaml file to the /data/excluded directory

  # yaml_files = ["data/1 - production-current-design-l3out-consumer.nac.yaml"]
  # yaml_files = ["data/2 - production-current-design-l3out-provider.nac.yaml"]
  # yaml_files = ["data/3 - production-dual-vrf-design-l3out-consumer.nac.yaml"]  
  # yaml_files = ["data/4 - production-dual-vrf-design-l3out-provider.nac.yaml"]
  # yaml_files = ["data/5 - production-dual-vrf-invalid-design-l3out-consumer-vzAny-provider.nac.yaml"]
  # yaml_files = ["data/6 - production-shared-l3out-design-l3out-consumer.nac.yaml"]
  # yaml_files = ["data/7 - production-shared-l3out-design-l3out-provider.nac.yaml"]
  # yaml_files = ["data/8 - production-dual-vrf-design-in-common-l3out-consumer.nac.yaml"]
  # yaml_files = ["data/9 - production-dual-vrf-design-in-common-l3out-provider.nac.yaml"]
  # yaml_files = ["data/10 - production-shared-l3out-design-l3out-provider-ssh-to-vzAny.nac.yaml"]
  # yaml_files = ["data/11 - production-shared-l3out-design-l3out-consumer-consolidated-BD-net-centric.nac.yaml"]
  yaml_files = ["data/12 - production-shared-l3out-design-l3out-consumer-consolidated-BD-app-centric.nac.yaml"]


  manage_access_policies    = false
  manage_fabric_policies    = false
  manage_pod_policies       = false
  manage_node_policies      = false
  manage_interface_policies = false
  manage_tenants            = true
}
