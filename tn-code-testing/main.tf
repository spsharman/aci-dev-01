terraform {
  required_providers {
    aci = {
      source  = "CiscoDevNet/aci"
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
  source  = "netascode/nac-aci/aci"

  yaml_directories = ["data"]

  manage_access_policies    = false
  manage_fabric_policies    = false
  manage_pod_policies       = false
  manage_node_policies      = false
  manage_interface_policies = false
  manage_tenants            = true
}

# Tenant created by NAC module
data "aci_tenant" "code-testing" {
  depends_on = [module.aci]
  name       = "code-testing"
}

# Create L4-7 Device
resource "aci_l4_l7_device" "ftd-4112-two-arm-L2" {
  tenant_dn                            = data.aci_tenant.code-testing.id
  name                                 = "ftd-4112-two-arm-L2"
  active                               = "yes"
  context_aware                        = "single-Context"
  device_type                          = "PHYSICAL"
  function_type                        = "L2"
  is_copy                              = "no"
  mode                                 = "legacy-Mode"
  promiscuous_mode                     = "no"
  service_type                         = "OTHERS"
  relation_vns_rs_al_dev_to_phys_dom_p = "uni/phys-firewalls"
}

# Create the L4-7 Cluster
resource "aci_concrete_device" "ftd-4112-cluster" {
  l4_l7_device_dn = aci_l4_l7_device.ftd-4112-two-arm-L2.id
  name            = "ftd-4112-cluster"
}

# Add concrete interface
resource "aci_concrete_interface" "ftd-data-01-vlan-12" {
  concrete_device_dn            = aci_concrete_device.ftd-4112-cluster.id
  name                          = "data-01-vlan-12-L2"
  encap                         = "vlan-12"
  relation_vns_rs_c_if_path_att = "topology/pod-1/protpaths-101-102/pathep-[vpc_to_ftd-4112-cluster-data-01]"
}

# Add concrete interface
resource "aci_concrete_interface" "ftd-data-02-vlan-13" {
  concrete_device_dn            = aci_concrete_device.ftd-4112-cluster.id
  name                          = "data-02-vlan-13-L2"
  encap                         = "vlan-13"
  relation_vns_rs_c_if_path_att = "topology/pod-1/protpaths-101-102/pathep-[vpc_to_ftd-4112-cluster-data-02]"
}

# Add logical interface
resource "aci_l4_l7_logical_interface" "consumer" {
  l4_l7_device_dn            = aci_l4_l7_device.ftd-4112-two-arm-L2.id
  name                       = "consumer"
  relation_vns_rs_c_if_att_n = [aci_concrete_interface.ftd-data-01-vlan-12.id]
}

# Add logical interface
resource "aci_l4_l7_logical_interface" "provider" {
  l4_l7_device_dn            = aci_l4_l7_device.ftd-4112-two-arm-L2.id
  name                       = "provider"
  relation_vns_rs_c_if_att_n = [aci_concrete_interface.ftd-data-02-vlan-13.id]
}

# Create L4-L7 Service Graph template
resource "aci_l4_l7_service_graph_template" "ftd-4112-two-arm-L2" {
  tenant_dn                         = data.aci_tenant.code-testing.id
  name                              = "ftd-4112-two-arm-L2"
  l4_l7_service_graph_template_type = "legacy"
  ui_template_type                  = "UNSPECIFIED"
  term_cons_name                    = "T1"
  term_prov_name                    = "T2"
}

# Create L4-L7 Service Graph template node
resource "aci_function_node" "N1" {
  l4_l7_service_graph_template_dn      = aci_l4_l7_service_graph_template.ftd-4112-two-arm-L2.id
  name                                 = "N1"
  func_template_type                   = "OTHER"
  func_type                            = "L2"
  managed                              = "no"
  routing_mode                         = "Redirect"
  l4_l7_device_interface_consumer_name = "consumer"
  l4_l7_device_interface_provider_name = "provider"
  relation_vns_rs_node_to_l_dev        = "uni/tn-code-testing/lDevVip-ftd-4112-two-arm-L2"
}

# Add consumer interface
resource "aci_connection" "N1-consumer" {
  l4_l7_service_graph_template_dn = aci_l4_l7_service_graph_template.ftd-4112-two-arm-L2.id
  name                            = "C1"
  adj_type                        = "L3"
  conn_dir                        = "consumer"
  conn_type                       = "internal"
  direct_connect                  = "yes"
  unicast_route                   = "yes"
  relation_vns_rs_abs_connection_conns = [
    aci_l4_l7_service_graph_template.ftd-4112-two-arm-L2.term_cons_dn,
    aci_function_node.N1.conn_consumer_dn
  ]
}

# Add provider interface
resource "aci_connection" "N1-provider" {
  l4_l7_service_graph_template_dn = aci_l4_l7_service_graph_template.ftd-4112-two-arm-L2.id
  name                            = "C2"
  adj_type                        = "L3"
  conn_dir                        = "provider"
  conn_type                       = "internal"
  direct_connect                  = "yes"
  unicast_route                   = "yes"
  relation_vns_rs_abs_connection_conns = [
    aci_l4_l7_service_graph_template.ftd-4112-two-arm-L2.term_prov_dn,
    aci_function_node.N1.conn_provider_dn
  ]
}

# Create L4-L7 Device Selection Policy
resource "aci_logical_device_context" "ftd-4112-two-arm-L2" {
  tenant_dn                          = data.aci_tenant.code-testing.id
  ctrct_name_or_lbl                  = "any"
  graph_name_or_lbl                  = "ftd-4112-two-arm-L2"
  node_name_or_lbl                   = "N1"
  relation_vns_rs_l_dev_ctx_to_l_dev = "uni/tn-code-testing/lDevVip-ftd-4112-two-arm-L2"
}

# Create L4-L7 Device Selection Policy Interface
resource "aci_logical_interface_context" "consumer" {
  logical_device_context_dn        = aci_logical_device_context.ftd-4112-two-arm-L2.id
  conn_name_or_lbl                 = "consumer"
  l3_dest                          = "yes"
  permit_log                       = "no"
  relation_vns_rs_l_if_ctx_to_l_if = "uni/tn-code-testing/lDevVip-ftd-4112-two-arm-L2/lIf-consumer"
  relation_vns_rs_l_if_ctx_to_bd   = "uni/tn-code-testing/BD-ftd-4112-consumer-L2"
  # relation_vns_rs_l_if_ctx_to_svc_redirect_pol = ""

}

# Create L4-L7 Device Selection Policy Interface
resource "aci_logical_interface_context" "provider" {
  logical_device_context_dn        = aci_logical_device_context.ftd-4112-two-arm-L2.id
  conn_name_or_lbl                 = "provider"
  l3_dest                          = "yes"
  permit_log                       = "no"
  relation_vns_rs_l_if_ctx_to_l_if = "uni/tn-code-testing/lDevVip-ftd-4112-two-arm-L2/lIf-provider"
  relation_vns_rs_l_if_ctx_to_bd   = "uni/tn-code-testing/BD-ftd-4112-provider-L2"
  # relation_vns_rs_l_if_ctx_to_svc_redirect_pol = ""
}