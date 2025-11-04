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

  # yaml_files = ["data/01-production-current-design-vzAny-allows-open-communication.nac.yaml"]
  # yaml_files = ["data/02-production-dual-vrf-design-l3out-consumer.nac.yaml"]  
  # yaml_files = ["data/03-production-dual-vrf-design-l3out-provider.nac.yaml"]
  # yaml_files = ["data/04-production-dual-vrf-invalid-design-l3out-consumer-vzAny-provider.nac.yaml"]
  # yaml_files = ["data/05-production-shared-l3out-design-l3out-consumer.nac.yaml"]
  # yaml_files = ["data/06-production-shared-l3out-design-l3out-provider.nac.yaml"]
  # yaml_files = ["data/07-production-dual-vrf-design-in-common-l3out-consumer.nac.yaml"]
  # yaml_files = ["data/08-production-dual-vrf-design-in-common-l3out-provider.nac.yaml"]
  # yaml_files = ["data/09-production-shared-l3out-design-l3out-provider-ssh-to-vzAny.nac.yaml"]
  # yaml_files = ["data/10-production-shared-l3out-design-l3out-consumer-consolidated-BD-net-centric.nac.yaml"]
  # yaml_files = ["data/11-production-shared-l3out-design-l3out-consumer-consolidated-BD-app-centric.nac.yaml"]
  # yaml_files = ["data/12-production-single-vrf-design-esg-l3out-consumer.nac.yaml"]
  # yaml_files = ["data/13-production-shared-l3out-design-esg-l3out-consumer.nac.yaml"]
  # yaml_files = ["data/14-production-shared-l3out-design-esg-l3out-consumer-with-vzAny.nac.yaml"]
  # yaml_files = ["data/15-production-shared-l3out-design-with-fw-esg-l3out-consumer.nac.yaml"]
  # yaml_files = ["data/16-production-dual-l3out-design-with-fw-esg-l3out-consumer.nac.yaml"]
  # yaml_files = ["data/17-production-single-vrf-dual-l3out-design-with-nat.nac.yaml"]
  yaml_files = ["data/18-production-dual-vrf-l3out-design-with-nat.nac.yaml"]
  # yaml_files = ["data/19-production-dual-vrf-l3out-design-with-nat-uni-directional-contracts.nac.yaml"]
  # yaml_files = ["data/20-production-dual-vrf-l3out-design-with-nat-fw-redirect-l3out.nac.yaml"]


  manage_access_policies    = false
  manage_fabric_policies    = false
  manage_pod_policies       = false
  manage_node_policies      = false
  manage_interface_policies = false
  manage_tenants            = true
}
