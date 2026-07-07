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
  version = "1.2.0"
  
  # source = "github.com/netascode/terraform-aci-nac-aci?ref=main"

  # yaml_files = ["bgp-applied-to-node/00-base-network.nac.yaml"]
  # yaml_files = ["bgp-applied-to-node/01-add-split-vrf.nac.yaml"]
  # yaml_files = ["bgp-applied-to-node/02-add-route-leaking.nac.yaml"]    
  # yaml_files = ["bgp-applied-to-node/03-epg-to-esg-mapping.nac.yaml"]   
  # yaml_files = ["bgp-applied-to-node/04-add-ftdv-north-south-flows.nac.yaml"]   
  # yaml_files = ["bgp-applied-to-node/05-add-ss-east-west-flows.nac.yaml"]   
  # yaml_files = ["bgp-applied-to-node/06-add-ftdv-east-west-flows.nac.yaml"]   
  # yaml_files = ["bgp-applied-to-node/07-add-contract-to-each-esg.nac.yaml"]
  # yaml_files = ["bgp-applied-to-node/08-add-application-esgs-and-contracts.nac.yaml"]
  yaml_files = ["bgp-applied-to-node/09-add-intra-application-contracts.nac.yaml"]
  
  
  manage_access_policies    = false
  manage_fabric_policies    = false
  manage_pod_policies       = false
  manage_node_policies      = false
  manage_interface_policies = false
  manage_tenants            = true
}
