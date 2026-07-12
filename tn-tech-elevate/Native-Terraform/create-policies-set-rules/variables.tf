variable "apic_username" {
  type        = string
  description = "APIC username."
}

variable "apic_password" {
  type        = string
  description = "APIC password."
}

variable "apic_url" {
  type        = string
  description = "APIC URL (for example, https://apic.example.local)."
}

variable "set_rules" {
  type = map(object({
    tenant_name              = string
    application_name         = string
    application_profile_name = string
    esg_name                 = string
  }))
  description = "Set rules keyed by a unique rule key. Each rule creates rtctrlAttrP and links sptag to an ESG."
}
