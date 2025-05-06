# variables.tf

# vSphere connection details variable
variable "vcenter_username" {
  type = string
}

variable "vcenter_password" {
  type = string
}

variable "vcenter_url" {
  type = string
}

# Datacenter name
variable "datacenter_name" {
  type        = string
  description = "The name of the datacenter"
  default     = "ACI"
}

# Distributed Virtual Switch Name
variable "vds_name" {
  type        = string
  description = "The name of the distributed virtual switch"
  default     = "hx-dev-01-vds-02"
}

# Primary and Secondary VLANs for PVLAN mappings - need to ensure VLANs are configured in access policies
variable "primary_vlan_ids" {
  type        = list(number)
  description = "List of primary VLAN IDs for PVLAN configuration"
  default     = [22, 24, 26, 28, 30, 32, 34]
}

variable "secondary_vlan_ids" {
  type        = map(list(number))
  description = "Mapping of primary VLAN to secondary VLANs"
  default = {
    22 = [22, 23] # Promiscuous, Isolated
    24 = [24, 25] # Promiscuous, Isolated
    26 = [26, 27] # Promiscuous, Isolated
    28 = [28, 29] # Promiscuous, Isolated
    30 = [30, 31] # Promiscuous, Isolated
    32 = [32, 33] # Promiscuous, Isolated
    34 = [34, 35] # Promiscuous, Isolated
  }
}

# PVLAN Port Groups Configuration
variable "pvlan-portgroups" {
  type        = map(number)
  description = "Port groups and their associated secondary VLAN IDs"
  default = {
    # Port group name should follow the ACI structure 'tenant|application profile|epg'
    # Example "adealdag|network-segments|192.168.40.0_24" = 3011
  }
}

# Access Port Groups Configuration
variable "access-portgroups" {
  type        = map(number)
  description = "Access Port groups"
  default = {
    "shared-services.vrf-01-ospf-area-0.0.0.0" = 8
    "demo-01.vrf-01-ospf-area-0.0.0.0" = 9
    "BRKDCN-2959-DMZ.vrf-01-ospf-area-0.0.0.0" = 30
    # "demo-03.vrf-01-bgp-AS-65151" = 11
    "isovalent.vrf-01-bgp-AS-65152" = 16
  }
}
