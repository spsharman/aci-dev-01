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

variable "nac_yaml_file" {
  type        = string
  description = "Path to the NAC YAML file used as source of truth."
}

variable "tenant_name" {
  type        = string
  description = "Tenant to select from the NAC YAML (without tn- prefix)."
}

variable "application_profile_name" {
  type        = string
  description = "Application profile name to select from the NAC YAML (without ap- prefix)."
}

variable "exclude_esg_names" {
  type        = list(string)
  description = "Optional list of ESG names to exclude from set-rule generation."
  default     = []
}
