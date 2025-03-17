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

  # yaml_directories = ["data"]
  yaml_files = ["users.nac.yaml"]

  manage_access_policies    = false
  manage_fabric_policies    = true
  manage_pod_policies       = false
  manage_node_policies      = false
  manage_interface_policies = false
  manage_tenants            = true
}

# data "aci_tenant" "fgandola" {
#   depends_on = [module.aci]
#   name       = "fgandola"
# }

# resource "aci_l4_l7_device" "ftd-4112-two-arm-L2" {
#   tenant_dn                            = data.aci_tenant.fgandola.id
#   name                                 = "ftd-4112-two-arm-L2"
#   active                               = "yes"
#   context_aware                        = "single-Context"
#   device_type                          = "PHYSICAL"
#   function_type                        = "L2"
#   is_copy                              = "no"
#   mode                                 = "legacy-Mode"
#   promiscuous_mode                     = "no"
#   service_type                         = "OTHERS"
#   relation_vns_rs_al_dev_to_phys_dom_p = "uni/phys-firewalls"
# }

# resource "aci_concrete_device" "ftd-4112-cluster" {
#   l4_l7_device_dn = aci_l4_l7_device.ftd-4112-two-arm-L2.id
#   name            = "ftd-4112-cluster"
# }

# resource "aci_concrete_interface" "ftd-data-01-vlan-12" {
#   concrete_device_dn            = aci_concrete_device.ftd-4112-cluster.id
#   name                          = "data-01-vlan-12"
#   encap                         = "vlan-12"
#   relation_vns_rs_c_if_path_att = "topology/pod-1/protpaths-101-102/pathep-[vpc_to_ftd-4112-cluster-data-01]"
# }

# resource "aci_concrete_interface" "ftd-data-02-vlan-13" {
#   concrete_device_dn            = aci_concrete_device.ftd-4112-cluster.id
#   name                          = "data-02-vlan-13"
#   encap                         = "vlan-13"
#   relation_vns_rs_c_if_path_att = "topology/pod-1/protpaths-101-102/pathep-[vpc_to_ftd-4112-cluster-data-02]"
# }

# resource "aci_l4_l7_logical_interface" "consumer" {
#   l4_l7_device_dn            = aci_l4_l7_device.ftd-4112-two-arm-L2.id
#   name                       = "consumer"
#   relation_vns_rs_c_if_att_n = [aci_concrete_interface.ftd-data-01-vlan-12.id]
# }

# resource "aci_l4_l7_logical_interface" "provider" {
#   l4_l7_device_dn            = aci_l4_l7_device.ftd-4112-two-arm-L2.id
#   name                       = "provider"
#   relation_vns_rs_c_if_att_n = [aci_concrete_interface.ftd-data-02-vlan-13.id]
# }

# resource "aci_l4_l7_service_graph_template" "ftd-4112-two-arm-L2" {
#   tenant_dn                         = data.aci_tenant.fgandola.id
#   name                              = "ftd-4112-two-arm-L2"
#   l4_l7_service_graph_template_type = "legacy"
#   ui_template_type                  = "UNSPECIFIED"
#   term_cons_name                    = "T1"
#   term_prov_name                    = "T2"
# }

# resource "aci_function_node" "N1" {
#   l4_l7_service_graph_template_dn      = aci_l4_l7_service_graph_template.ftd-4112-two-arm-L2.id
#   name                                 = "N1"
#   func_template_type                   = "OTHER"
#   func_type                            = "L2"
#   managed                              = "no"
#   routing_mode                         = "Redirect"
#   l4_l7_device_interface_consumer_name = "consumer"
#   l4_l7_device_interface_provider_name = "provider"
#   relation_vns_rs_node_to_abs_func_prof = "uni/tn-fgandola/AbsGraph-ftd-4112-two-arm-L2/AbsNode-N1"
# }

# resource "aci_connection" "N1-consumer" {
#   l4_l7_service_graph_template_dn  = aci_l4_l7_service_graph_template.ftd-4112-two-arm-L2.id
#   name  = "C1"
#   adj_type  = "L3"
#   conn_dir  = "consumer"
#   conn_type  = "internal"
#   direct_connect  = "yes"
#   unicast_route  = "yes"
#   relation_vns_rs_abs_connection_conns = [
#     aci_l4_l7_service_graph_template.ftd-4112-two-arm-L2.term_cons_dn,
#     aci_function_node.N1.conn_consumer_dn
#   ]
# }

# resource "aci_connection" "N1-provider" {
#   l4_l7_service_graph_template_dn  = aci_l4_l7_service_graph_template.ftd-4112-two-arm-L2.id
#   name  = "C2"
#   adj_type  = "L3"
#   conn_dir  = "provider"
#   conn_type  = "internal"
#   direct_connect  = "yes"
#   unicast_route  = "yes"
#   relation_vns_rs_abs_connection_conns = [
#     aci_l4_l7_service_graph_template.ftd-4112-two-arm-L2.term_prov_dn,
#     aci_function_node.N1.conn_provider_dn
#   ]
# }

# aci_function_node.N1: Modifying... [id=uni/tn-fgandola/AbsGraph-ftd-4112-two-arm-L2/AbsNode-N1]
# aci_function_node.N1: Modifications complete after 1s [id=uni/tn-fgandola/AbsGraph-ftd-4112-two-arm-L2/AbsNode-N1]