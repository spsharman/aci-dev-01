# APIC credentials and URL
# variable "credentials" {
#   type = map(string)
#   default = {
#     apic_username = "some-username"
#     apic_password = "some-password"
#     apic_url      = "some-url"
#   }
#   sensitive = true
# }

variable "apic_username" {
  type = string
}

variable "apic_password" {
  type = string
}

variable "apic_url" {
  type = string
}

# Name of tenant that contains your applications
variable "tenant" {
  default = "demo-non-vmm"
}

# Name of VRF containing IP addresses associated with your applications
variable "vrf" {
  default = "vrf-01"
}

# Name for each ESG
variable "esg" {
  default = "all-services"
}

# Name of EXISTING contract to provide any-any communication through vzAny
variable "permit-any-contract" {
  default = "permit-to-all-applications"
}

# Name of each application profile
variable "app_profiles" {
  default = ["online-boutique"]
}

# Map of each IP address and their associated application tag.
variable "ips" {
  default = {
    "10.0.11.101" = {
      app = "online-boutique"
    },
    "10.0.11.102" = {
      app = "online-boutique"
    },
    "10.0.11.103" = {
      app = "online-boutique"
    },
    "10.0.12.101" = {
      app = "online-boutique"
    },
    "10.0.12.102" = {
      app = "online-boutique"
    },
    "10.0.13.100" = {
      app = "online-boutique"
    },
    "10.0.13.101" = {
      app = "online-boutique"
    },
    "10.0.14.100" = {
      app = "online-boutique"
    },
    "10.0.14.101" = {
      app = "online-boutique"
    }
  }
}