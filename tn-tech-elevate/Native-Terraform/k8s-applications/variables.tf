variable "apic_username" {
  description = "APIC username."
  type        = string
}

variable "apic_password" {
  description = "APIC password."
  type        = string
  sensitive   = true
}

variable "apic_url" {
  description = "APIC URL (for example, https://apic.example.local)."
  type        = string
}

variable "tenant_name" {
  description = "ACI tenant name. Accepts both tn-tech-elevate and tech-elevate."
  type        = string
  default     = "tn-tech-elevate"
}

variable "vrf_name" {
  description = "VRF used for ESG scope."
  type        = string
}

variable "contract_prefix" {
  description = "Prefix for provided contract names."
  type        = string
  default     = "permit-to"
}

variable "consumed_contract_prefix" {
  description = "Prefix for consumed contract names."
  type        = string
  default     = "permit-from"
}

variable "intra_contract_prefix" {
  description = "Prefix for optional intra-ESG contract names."
  type        = string
  default     = "permit-intra"
}

variable "contract_scope" {
  description = "Default scope applied to provided and consumed contracts when app-level overrides are not set."
  type        = string
  default     = "context"

  validation {
    condition     = contains(["context", "tenant", "global"], lower(var.contract_scope))
    error_message = "contract_scope must be one of: context, tenant, global."
  }
}

variable "default_provided_contract_consumer_esg_dns" {
  description = "Default ESG DN list that should consume each app provided contract."
  type        = set(string)
  default     = ["uni/tn-tech-elevate/ap-external-subnets/esg-all-external-subnets"]
}

variable "default_consumed_contract_provider_dns" {
  description = "Default provided contract DN list that each app ESG should consume."
  type        = set(string)
  default     = ["uni/tn-tech-elevate/brc-permit-to-all-external-subnets"]
}

variable "k8s_applications_yaml_file" {
  description = "Optional YAML file path. When present, k8s_applications are loaded from this file."
  type        = string
  default     = "k8s-applications.yaml"
}

variable "k8s_applications" {
  description = <<-EOT
    K8s applications keyed by a unique ID (for example: "payments-api").
    Naming is generated as:
      - application profile: k8s.ns.namespace.application_name
      - ESG: application_name
      - provided contract: {contract_prefix}-k8s.ns.namespace.application_name
      - consumed contract: {consumed_contract_prefix}-k8s.ns.namespace.application_name
      - optional intra-ESG contract: {intra_contract_prefix}-k8s.ns.namespace.application_name
      - external subnet selectors: one selector per CIDR in external_subnets

    Each application defines direction-specific rules:
      - contract_rules_in  -> provided contract filters (<proto>-in-...)
      - contract_rules_out -> consumed contract filters (<proto>-out-...)
      - provided_contract_consumer_esg_dns -> external ESG DNs that consume this app provided contract
      - consumed_contract_provider_dns -> provided contract DNs this app ESG consumes

    Allowed subject values: TCP, UDP, ICMP, Redirect.
  EOT

  type = map(object({
    namespace                          = string
    application_name                   = string
    enable_intra_esg_contract          = optional(bool, false)
    provided_contract_scope            = optional(string)
    consumed_contract_scope            = optional(string)
    provided_contract_consumer_esg_dns = optional(set(string), [])
    consumed_contract_provider_dns     = optional(set(string), [])
    external_subnets                   = set(string)
    contract_rules_in = list(object({
      subject          = string
      source_port      = string
      destination_port = string
      stateful         = optional(bool, true)
      service_graph    = optional(string)
    }))
    contract_rules_out = list(object({
      subject          = string
      source_port      = string
      destination_port = string
      stateful         = optional(bool, true)
      service_graph    = optional(string)
    }))
  }))
  default = {}

  validation {
    condition = alltrue([
      for app in values(var.k8s_applications) :
      app.provided_contract_scope == null || contains(["context", "tenant", "global"], lower(app.provided_contract_scope))
    ])
    error_message = "provided_contract_scope must be one of: context, tenant, global."
  }

  validation {
    condition = alltrue([
      for app in values(var.k8s_applications) :
      alltrue([
        for dn in app.provided_contract_consumer_esg_dns :
        can(regex("^uni/tn-[^/]+/ap-[^/]+/esg-[^/]+$", dn))
      ])
    ])
    error_message = "Each provided_contract_consumer_esg_dns entry must be an ESG DN (for example: uni/tn-tech-elevate/ap-external-subnets/esg-all-external-subnets)."
  }

  validation {
    condition = alltrue([
      for app in values(var.k8s_applications) :
      alltrue([
        for dn in app.consumed_contract_provider_dns :
        can(regex("^uni/tn-[^/]+/brc-[^/]+$", dn))
      ])
    ])
    error_message = "Each consumed_contract_provider_dns entry must be a contract DN (for example: uni/tn-tech-elevate/brc-permit-to-all-external-subnets)."
  }

  validation {
    condition = alltrue([
      for app in values(var.k8s_applications) :
      app.consumed_contract_scope == null || contains(["context", "tenant", "global"], lower(app.consumed_contract_scope))
    ])
    error_message = "consumed_contract_scope must be one of: context, tenant, global."
  }

  validation {
    condition = alltrue(flatten([
      for app in values(var.k8s_applications) : [
        for subnet in app.external_subnets :
        can(cidrhost(subnet, 0))
      ]
    ]))
    error_message = "Each external_subnets value must be a valid CIDR (for single IPs, use /32)."
  }

  validation {
    condition = alltrue(flatten([
      for app in values(var.k8s_applications) : [
        for rule in concat(app.contract_rules_in, app.contract_rules_out) :
        contains(["TCP", "UDP", "ICMP", "REDIRECT"], upper(rule.subject))
      ]
    ]))
    error_message = "Each contract_rules.subject must be one of: TCP, UDP, ICMP, Redirect."
  }

  validation {
    condition = alltrue(flatten([
      for app in values(var.k8s_applications) : [
        for rule in concat(app.contract_rules_in, app.contract_rules_out) :
        (
          lower(rule.source_port) == "any" ||
          (can(tonumber(rule.source_port)) && tonumber(rule.source_port) >= 1 && tonumber(rule.source_port) <= 65535)
        )
      ]
    ]))
    error_message = "Each contract_rules.source_port must be 'any' or a numeric port between 1 and 65535."
  }

  validation {
    condition = alltrue(flatten([
      for app in values(var.k8s_applications) : [
        for rule in concat(app.contract_rules_in, app.contract_rules_out) :
        (
          lower(rule.destination_port) == "any" ||
          (can(tonumber(rule.destination_port)) && tonumber(rule.destination_port) >= 1 && tonumber(rule.destination_port) <= 65535)
        )
      ]
    ]))
    error_message = "Each contract_rules.destination_port must be 'any' or a numeric port between 1 and 65535."
  }

  validation {
    condition = alltrue([
      for app in values(var.k8s_applications) :
      length(distinct([
        for rule in app.contract_rules_in : upper(rule.subject)
      ])) == length(app.contract_rules_in)
    ])
    error_message = "Each application must use unique subjects in contract_rules_in (one rule per subject)."
  }

  validation {
    condition = alltrue([
      for app in values(var.k8s_applications) :
      length(distinct([
        for rule in app.contract_rules_out : upper(rule.subject)
      ])) == length(app.contract_rules_out)
    ])
    error_message = "Each application must use unique subjects in contract_rules_out (one rule per subject)."
  }
}
