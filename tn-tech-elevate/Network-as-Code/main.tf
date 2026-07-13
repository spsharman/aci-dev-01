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

  # yaml_files = ["data/00-base-network.nac.yaml"]
  # yaml_files = ["data/01-add-split-vrf.nac.yaml"]
  # yaml_files = ["data/02-migrate-to-esgs.nac.yaml"]
  # yaml_files = ["data/03-add-ftdv-for-north-south-flows.nac.yaml"]
  # yaml_files = ["data/04-add-ss-and-ftdv-for-east-west-flows.nac.yaml"]
  yaml_files = ["data/05-add-k8s-auto-esg-assignment.nac.yaml"]
  # yaml_files = ["data/66-test-dual-vrf.nac.yaml"]
  # yaml_files = ["data/67-test-single-vrf.nac.yaml"]

  # yaml_files = ["data/08-add-application-esgs-and-contracts.nac.yaml"]
  # yaml_files = ["data/09-add-intra-application-contracts.nac.yaml"]


  manage_access_policies    = false
  manage_fabric_policies    = false
  manage_pod_policies       = false
  manage_node_policies      = false
  manage_interface_policies = false
  manage_tenants            = true
}
