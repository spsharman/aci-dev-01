terraform {
  required_providers {
    aci = {
      source  = "CiscoDevNet/aci"
      version = ">= 2.0.0"
    }
  }
}

provider "aci" {
  username = var.apic_username
  password = var.apic_password
  url      = var.apic_url
}

locals {
  normalized_tenant_name = startswith(var.tenant_name, "tn-") ? substr(var.tenant_name, 3, length(var.tenant_name) - 3) : var.tenant_name
  tenant_dn              = "uni/tn-${local.normalized_tenant_name}"

  aci_name_max_length    = 64
  aci_hash_length        = 8
  aci_name_prefix_length = local.aci_name_max_length - local.aci_hash_length - 1

  yaml_configuration = (
    var.k8s_applications_yaml_file != null && fileexists(var.k8s_applications_yaml_file)
    ? yamldecode(file(var.k8s_applications_yaml_file))
    : {}
  )

  yaml_applications = {
    for app_key, application in try(local.yaml_configuration.k8s_applications, {}) :
    app_key => {
      namespace                 = tostring(application.namespace)
      application_name          = tostring(application.application_name)
      enable_intra_esg_contract = try(tobool(application.enable_intra_esg_contract), false)
      provided_contract_scope   = try(tostring(application.provided_contract_scope), "")
      consumed_contract_scope   = try(tostring(application.consumed_contract_scope), "")
      external_subnets          = toset(try(application.external_subnets, []))
      contract_rules_in = [
        for rule in try(application.contract_rules_in, []) : {
          subject          = tostring(rule.subject)
          source_port      = tostring(rule.source_port)
          destination_port = tostring(rule.destination_port)
          stateful         = try(tobool(rule.stateful), true)
          service_graph    = try(tostring(rule.service_graph), "")
        }
      ]
      contract_rules_out = [
        for rule in try(application.contract_rules_out, []) : {
          subject          = tostring(rule.subject)
          source_port      = tostring(rule.source_port)
          destination_port = tostring(rule.destination_port)
          stateful         = try(tobool(rule.stateful), true)
          service_graph    = try(tostring(rule.service_graph), "")
        }
      ]
    }
  }
  applications = length(var.k8s_applications) > 0 ? var.k8s_applications : local.yaml_applications

  application_identifiers = {
    for app_key, application in local.applications :
    app_key => "k8s.ns.${application.namespace}.${application.application_name}"
  }

  application_profile_names = {
    for app_key, identifier in local.application_identifiers :
    app_key => (
      length(identifier) <= local.aci_name_max_length
      ? identifier
      : "${substr(identifier, 0, local.aci_name_prefix_length)}-${substr(sha1(identifier), 0, local.aci_hash_length)}"
    )
  }

  application_esg_names = {
    for app_key, application in local.applications :
    app_key => (
      length(application.application_name) <= local.aci_name_max_length
      ? application.application_name
      : "${substr(application.application_name, 0, local.aci_name_prefix_length)}-${substr(sha1(application.application_name), 0, local.aci_hash_length)}"
    )
  }

  application_contract_names = {
    for app_key, identifier in local.application_identifiers :
    app_key => (
      length("${var.contract_prefix}-${identifier}") <= local.aci_name_max_length
      ? "${var.contract_prefix}-${identifier}"
      : "${substr("${var.contract_prefix}-${identifier}", 0, local.aci_name_prefix_length)}-${substr(sha1("${var.contract_prefix}-${identifier}"), 0, local.aci_hash_length)}"
    )
  }

  application_consumed_contract_names = {
    for app_key, identifier in local.application_identifiers :
    app_key => (
      length("${var.consumed_contract_prefix}-${identifier}") <= local.aci_name_max_length
      ? "${var.consumed_contract_prefix}-${identifier}"
      : "${substr("${var.consumed_contract_prefix}-${identifier}", 0, local.aci_name_prefix_length)}-${substr(sha1("${var.consumed_contract_prefix}-${identifier}"), 0, local.aci_hash_length)}"
    )
  }

  applications_with_intra_contract = {
    for app_key, application in local.applications :
    app_key => application
    if try(application.enable_intra_esg_contract, false)
  }

  application_intra_contract_names = {
    for app_key, identifier in local.application_identifiers :
    app_key => (
      length("${var.intra_contract_prefix}-${identifier}") <= local.aci_name_max_length
      ? "${var.intra_contract_prefix}-${identifier}"
      : "${substr("${var.intra_contract_prefix}-${identifier}", 0, local.aci_name_prefix_length)}-${substr(sha1("${var.intra_contract_prefix}-${identifier}"), 0, local.aci_hash_length)}"
    )
  }

  external_subnet_selectors = merge([
    for app_key, application in local.applications : {
      for subnet in application.external_subnets :
      "${app_key}::${subnet}" => {
        app_key = app_key
        subnet  = subnet
      }
    }
  ]...)

  contract_rules_in = merge([
    for app_key, application in local.applications : {
      for rule in application.contract_rules_in :
      "${app_key}::in::${upper(tostring(rule.subject))}" => {
        app_key = app_key

        subject_name = upper(tostring(rule.subject)) == "REDIRECT" ? "Redirect" : upper(tostring(rule.subject))

        subject_lower = lower(
          upper(tostring(rule.subject)) == "REDIRECT"
          ? "Redirect"
          : upper(tostring(rule.subject))
        )

        source_port_label = lower(tostring(rule.source_port)) == "any" ? "any" : tostring(rule.source_port)
        dest_port_label   = lower(tostring(rule.destination_port)) == "any" ? "any" : tostring(rule.destination_port)
        stateful_enabled  = try(rule.stateful, true)
        service_graph_dn  = try(trimspace(rule.service_graph), "") != "" ? trimspace(rule.service_graph) : null
      }
    }
  ]...)

  contract_rules_out = merge([
    for app_key, application in local.applications : {
      for rule in application.contract_rules_out :
      "${app_key}::out::${upper(tostring(rule.subject))}" => {
        app_key = app_key

        subject_name = upper(tostring(rule.subject)) == "REDIRECT" ? "Redirect" : upper(tostring(rule.subject))

        subject_lower = lower(
          upper(tostring(rule.subject)) == "REDIRECT"
          ? "Redirect"
          : upper(tostring(rule.subject))
        )

        source_port_label = lower(tostring(rule.source_port)) == "any" ? "any" : tostring(rule.source_port)
        dest_port_label   = lower(tostring(rule.destination_port)) == "any" ? "any" : tostring(rule.destination_port)
        stateful_enabled  = try(rule.stateful, true)
        service_graph_dn  = try(trimspace(rule.service_graph), "") != "" ? trimspace(rule.service_graph) : null
      }
    }
  ]...)

  contract_rule_details_in = {
    for rule_key, rule in local.contract_rules_in :
    rule_key => merge(rule, {
      filter_in_full_name = "${local.application_identifiers[rule.app_key]}-${rule.subject_lower}-in-src-${rule.source_port_label}-dst-${rule.dest_port_label}"
      entry_full_name     = "${rule.subject_lower}-src-${rule.source_port_label}-dst-${rule.dest_port_label}"
      filter_protocol = (
        rule.subject_name == "TCP" ? "tcp" :
        rule.subject_name == "UDP" ? "udp" :
        rule.subject_name == "ICMP" ? "icmp" :
        "icmpv6"
      )
      ether_type = (
        rule.subject_name == "Redirect" ? "ipv6" :
        rule.subject_name == "ICMP" ? "ipv4" :
        "ip"
      )
      source_port_value = (
        contains(["TCP", "UDP"], rule.subject_name)
        ? (rule.source_port_label == "any" ? "unspecified" : rule.source_port_label)
        : "unspecified"
      )
      destination_port_value = (
        contains(["TCP", "UDP"], rule.subject_name)
        ? (rule.dest_port_label == "any" ? "unspecified" : rule.dest_port_label)
        : "unspecified"
      )
      icmpv6_type = rule.subject_name == "Redirect" ? "redirect" : "unspecified"
      stateful    = rule.stateful_enabled ? "yes" : "no"
    })
  }

  contract_rule_details_out = {
    for rule_key, rule in local.contract_rules_out :
    rule_key => merge(rule, {
      filter_out_full_name = "${local.application_identifiers[rule.app_key]}-${rule.subject_lower}-out-src-${rule.source_port_label}-dst-${rule.dest_port_label}"
      entry_full_name      = "${rule.subject_lower}-src-${rule.source_port_label}-dst-${rule.dest_port_label}"
      filter_protocol = (
        rule.subject_name == "TCP" ? "tcp" :
        rule.subject_name == "UDP" ? "udp" :
        rule.subject_name == "ICMP" ? "icmp" :
        "icmpv6"
      )
      ether_type = (
        rule.subject_name == "Redirect" ? "ipv6" :
        rule.subject_name == "ICMP" ? "ipv4" :
        "ip"
      )
      source_port_value = (
        contains(["TCP", "UDP"], rule.subject_name)
        ? (rule.source_port_label == "any" ? "unspecified" : rule.source_port_label)
        : "unspecified"
      )
      destination_port_value = (
        contains(["TCP", "UDP"], rule.subject_name)
        ? (rule.dest_port_label == "any" ? "unspecified" : rule.dest_port_label)
        : "unspecified"
      )
      icmpv6_type = rule.subject_name == "Redirect" ? "redirect" : "unspecified"
      stateful    = rule.stateful_enabled ? "yes" : "no"
    })
  }

  filter_in_names = {
    for rule_key, rule in local.contract_rule_details_in :
    rule_key => (
      length(rule.filter_in_full_name) <= local.aci_name_max_length
      ? rule.filter_in_full_name
      : "${substr(rule.filter_in_full_name, 0, local.aci_name_prefix_length)}-${substr(sha1(rule.filter_in_full_name), 0, local.aci_hash_length)}"
    )
  }

  filter_out_names = {
    for rule_key, rule in local.contract_rule_details_out :
    rule_key => (
      length(rule.filter_out_full_name) <= local.aci_name_max_length
      ? rule.filter_out_full_name
      : "${substr(rule.filter_out_full_name, 0, local.aci_name_prefix_length)}-${substr(sha1(rule.filter_out_full_name), 0, local.aci_hash_length)}"
    )
  }

  filter_entry_names = {
    for rule_key, rule in merge(local.contract_rule_details_in, local.contract_rule_details_out) :
    rule_key => (
      length(rule.entry_full_name) <= local.aci_name_max_length
      ? rule.entry_full_name
      : "${substr(rule.entry_full_name, 0, local.aci_name_prefix_length)}-${substr(sha1(rule.entry_full_name), 0, local.aci_hash_length)}"
    )
  }

  application_provided_contract_scopes = {
    for app_key, application in local.applications :
    app_key => (
      trimspace(try(application.provided_contract_scope, "")) != ""
      ? lower(trimspace(application.provided_contract_scope))
      : lower(var.contract_scope)
    )
  }

  application_consumed_contract_scopes = {
    for app_key, application in local.applications :
    app_key => (
      trimspace(try(application.consumed_contract_scope, "")) != ""
      ? lower(trimspace(application.consumed_contract_scope))
      : lower(var.contract_scope)
    )
  }

}

resource "aci_application_profile" "namespace" {
  for_each = local.applications

  parent_dn = local.tenant_dn
  name      = local.application_profile_names[each.key]
}

resource "aci_contract" "application" {
  for_each = local.applications

  tenant_dn = local.tenant_dn
  name      = local.application_contract_names[each.key]
  scope     = local.application_provided_contract_scopes[each.key]

  lifecycle {
    precondition {
      condition     = contains(["context", "tenant", "global"], local.application_provided_contract_scopes[each.key])
      error_message = "provided_contract_scope must be one of: context, tenant, global."
    }
  }
}

resource "aci_contract" "application_consumed" {
  for_each = local.applications

  tenant_dn = local.tenant_dn
  name      = local.application_consumed_contract_names[each.key]
  scope     = local.application_consumed_contract_scopes[each.key]

  lifecycle {
    precondition {
      condition     = contains(["context", "tenant", "global"], local.application_consumed_contract_scopes[each.key])
      error_message = "consumed_contract_scope must be one of: context, tenant, global."
    }
  }
}

resource "aci_contract" "application_intra" {
  for_each = local.applications_with_intra_contract

  tenant_dn = local.tenant_dn
  name      = local.application_intra_contract_names[each.key]
  scope     = "context"
}

resource "aci_endpoint_security_group" "application" {
  for_each = local.applications

  parent_dn = aci_application_profile.namespace[each.key].id
  name      = local.application_esg_names[each.key]

  relation_to_vrf = {
    vrf_name = var.vrf_name
  }

  relation_to_provided_contracts = [
    {
      contract_name = aci_contract.application[each.key].name
    }
  ]

  relation_to_consumed_contracts = [
    {
      contract_name = aci_contract.application_consumed[each.key].name
    }
  ]

  relation_to_intra_epg_contracts = try(each.value.enable_intra_esg_contract, false) ? [
    {
      contract_name = aci_contract.application_intra[each.key].name
    }
  ] : []
}

resource "aci_endpoint_security_group_selector" "application_external_subnet" {
  for_each = local.external_subnet_selectors

  endpoint_security_group_dn = aci_endpoint_security_group.application[each.value.app_key].id
  match_expression           = "ip=='${each.value.subnet}'"

  lifecycle {
    precondition {
      condition     = can(cidrhost(each.value.subnet, 0))
      error_message = "Each external subnet selector must be a valid CIDR."
    }
  }
}

resource "aci_contract_subject" "application_in" {
  for_each = local.contract_rule_details_in

  contract_dn                   = aci_contract.application[each.value.app_key].id
  name                          = each.value.subject_name
  relation_vz_rs_subj_graph_att = each.value.service_graph_dn

  lifecycle {
    precondition {
      condition     = contains(["TCP", "UDP", "ICMP", "Redirect"], each.value.subject_name)
      error_message = "Contract subject must be one of: TCP, UDP, ICMP, Redirect."
    }
  }
}

resource "aci_contract_subject" "application_out" {
  for_each = local.contract_rule_details_out

  contract_dn                   = aci_contract.application_consumed[each.value.app_key].id
  name                          = each.value.subject_name
  relation_vz_rs_subj_graph_att = each.value.service_graph_dn

  lifecycle {
    precondition {
      condition     = contains(["TCP", "UDP", "ICMP", "Redirect"], each.value.subject_name)
      error_message = "Contract subject must be one of: TCP, UDP, ICMP, Redirect."
    }
  }
}

resource "aci_filter" "application_in" {
  for_each = local.contract_rule_details_in

  tenant_dn = local.tenant_dn
  name      = local.filter_in_names[each.key]
}

resource "aci_filter" "application_out" {
  for_each = local.contract_rule_details_out

  tenant_dn = local.tenant_dn
  name      = local.filter_out_names[each.key]
}

resource "aci_filter_entry" "application_in" {
  for_each = local.contract_rule_details_in

  filter_dn   = aci_filter.application_in[each.key].id
  name        = local.filter_entry_names[each.key]
  ether_t     = each.value.ether_type
  prot        = each.value.filter_protocol
  s_from_port = each.value.source_port_value
  s_to_port   = each.value.source_port_value
  d_from_port = each.value.destination_port_value
  d_to_port   = each.value.destination_port_value
  icmpv6_t    = each.value.icmpv6_type
  stateful    = each.value.stateful

  lifecycle {
    precondition {
      condition = (
        each.value.source_port_label == "any" ||
        (can(tonumber(each.value.source_port_label)) && tonumber(each.value.source_port_label) >= 1 && tonumber(each.value.source_port_label) <= 65535)
      )
      error_message = "source_port must be 'any' or a numeric port between 1 and 65535."
    }

    precondition {
      condition = (
        each.value.dest_port_label == "any" ||
        (can(tonumber(each.value.dest_port_label)) && tonumber(each.value.dest_port_label) >= 1 && tonumber(each.value.dest_port_label) <= 65535)
      )
      error_message = "destination_port must be 'any' or a numeric port between 1 and 65535."
    }
  }
}

resource "aci_filter_entry" "application_out" {
  for_each = local.contract_rule_details_out

  filter_dn   = aci_filter.application_out[each.key].id
  name        = local.filter_entry_names[each.key]
  ether_t     = each.value.ether_type
  prot        = each.value.filter_protocol
  s_from_port = each.value.source_port_value
  s_to_port   = each.value.source_port_value
  d_from_port = each.value.destination_port_value
  d_to_port   = each.value.destination_port_value
  icmpv6_t    = each.value.icmpv6_type
  stateful    = each.value.stateful

  lifecycle {
    precondition {
      condition = (
        each.value.source_port_label == "any" ||
        (can(tonumber(each.value.source_port_label)) && tonumber(each.value.source_port_label) >= 1 && tonumber(each.value.source_port_label) <= 65535)
      )
      error_message = "source_port must be 'any' or a numeric port between 1 and 65535."
    }

    precondition {
      condition = (
        each.value.dest_port_label == "any" ||
        (can(tonumber(each.value.dest_port_label)) && tonumber(each.value.dest_port_label) >= 1 && tonumber(each.value.dest_port_label) <= 65535)
      )
      error_message = "destination_port must be 'any' or a numeric port between 1 and 65535."
    }
  }
}

resource "aci_contract_subject_filter" "application_in" {
  for_each = local.contract_rule_details_in

  contract_subject_dn = aci_contract_subject.application_in[each.key].id
  filter_dn           = aci_filter.application_in[each.key].id
  action              = "permit"
  directives          = ["none"]
}

resource "aci_contract_subject_filter" "application_out" {
  for_each = local.contract_rule_details_out

  contract_subject_dn = aci_contract_subject.application_out[each.key].id
  filter_dn           = aci_filter.application_out[each.key].id
  action              = "permit"
  directives          = ["none"]
}
