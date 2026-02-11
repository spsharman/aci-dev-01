variable "apic_username" {
  type = string
}

variable "apic_password" {
  type = string
}

variable "apic_url" {
  type = string
}

variable "application_details_file" {
  description = "CSV file containing tenant, application name, and IP address"
  type        = string
  default     = "application-details.csv"
}

variable "app_tag_key" {
  description = "Tag key for endpoint classification"
  type        = string
  default     = "ApplicationName"
}

variable "isolated" {
  description = "Default isolated value if CSV row does not specify it"
  type        = string
  default     = "unenforced"
}

variable "preferred_group" {
  description = "Default preferred-group value if CSV row does not specify it"
  type        = string
  default     = "exclude"
}