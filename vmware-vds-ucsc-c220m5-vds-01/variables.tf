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
  default     = "UKTME"
}

# Distributed Virtual Switch Name
variable "vds_name" {
  type        = string
  description = "The name of the distributed virtual switch"
  default     = "ucsc-c220m5-vds-01"
}

# Primary and Secondary VLANs for PVLAN mappings - need to ensure VLANs are configured in access policies
variable "primary_vlan_ids" {
  type        = list(number)
  description = "List of primary VLAN IDs for PVLAN configuration"
  default     = [3010, 3012, 3014, 3016, 3018, 3020, 3022, 3024, 3026, 3028]
}

variable "secondary_vlan_ids" {
  type        = map(list(number))
  description = "Mapping of primary VLAN to secondary VLANs"
  default = {
    3010 = [3010, 3011] # Promiscuous, Isolated
    3012 = [3012, 3013] # Promiscuous, Isolated
    3014 = [3014, 3015] # Promiscuous, Isolated
    3016 = [3016, 3017] # Promiscuous, Isolated
    3018 = [3018, 3019] # Promiscuous, Isolated
    3020 = [3020, 3021] # Promiscuous, Isolated
    3022 = [3022, 3023] # Promiscuous, Isolated
    3024 = [3024, 3025] # Promiscuous, Isolated
    3026 = [3026, 3027] # Promiscuous, Isolated
    3028 = [3028, 3029] # Promiscuous, Isolated
  }
}

# PVLAN Port Groups Configuration
variable "pvlan-portgroups" {
  type        = map(number)
  description = "Port groups and their associated secondary VLAN IDs"
  default = {
# Port group name should follow the ACI structure 'tenant|application profile|epg'
    "adealdag|network-segments|192.168.40.0_24" = 3011
    "adealdag|network-segments|192.168.41.0_24" = 3013
    "demo-02|network-segments|10.0.61.0_24" = 3015
    "demo-02|network-segments|10.0.62.0_24" = 3017
    "demo-03|network-segments|10.0.71.0_24" = 3019
    "demo-03|network-segments|10.0.72.0_24" = 3021
  }
}

# Access Port Groups Configuration
variable "access-portgroups" {
  type        = map(number)
  description = "Access Port groups"
  default = {
    "vmotion"        = 986
    "esx-management" = 992
    "ip-storage"     = 3002
  }
}
