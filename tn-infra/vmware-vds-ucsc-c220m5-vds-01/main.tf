# main.tf

provider "vsphere" {
  user           = var.vcenter_username
  password       = var.vcenter_password
  vsphere_server = var.vcenter_url

  allow_unverified_ssl = true
}

# Data source for the vSphere datacenter
data "vsphere_datacenter" "dc" {
  name = var.datacenter_name
}

# Distributed Virtual Switch configuration with dynamic PVLAN mappings
resource "vsphere_distributed_virtual_switch" "vds_config" {
  datacenter_id = data.vsphere_datacenter.dc.id
  name          = var.vds_name

  # Define Promiscuous and Isolated PVLANs using dynamic blocks
  dynamic "pvlan_mapping" {
    for_each = var.primary_vlan_ids
    content {
      primary_vlan_id   = pvlan_mapping.value
      secondary_vlan_id = pvlan_mapping.value
      pvlan_type        = "promiscuous"
    }
  }

  dynamic "pvlan_mapping" {
    for_each = var.secondary_vlan_ids
    content {
      primary_vlan_id   = pvlan_mapping.key
      secondary_vlan_id = pvlan_mapping.value[1]
      pvlan_type        = "isolated"
    }
  }
}

# Port Group configurations using variables and for_each
resource "vsphere_distributed_port_group" "pvlan-pg" {
  for_each = var.pvlan-portgroups
  name                            = each.key
  distributed_virtual_switch_uuid = vsphere_distributed_virtual_switch.vds_config.id
  port_private_secondary_vlan_id  = each.value
}

# Add a distributed port group
resource "vsphere_distributed_port_group" "access-pg" {
  # name                            = "pg-01"
  # distributed_virtual_switch_uuid = vsphere_distributed_virtual_switch.vds_config.id

  # vlan_id = 1000
  for_each = var.access-portgroups
  name                            = each.key
  distributed_virtual_switch_uuid = vsphere_distributed_virtual_switch.vds_config.id

  vlan_id = each.value
}