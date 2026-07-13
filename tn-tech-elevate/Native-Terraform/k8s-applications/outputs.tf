output "application_profiles" {
  description = "Application profile names created per application key."
  value = {
    for app_key, profile in aci_application_profile.namespace :
    app_key => profile.name
  }
}

output "endpoint_security_groups" {
  description = "ESG names and generated contract/subnet selector details per application key."
  value = {
    for app_key, esg in aci_endpoint_security_group.application :
    app_key => {
      esg_name               = esg.name
      provided_contract_name = local.application_contract_names[app_key]
      consumed_contract_name = local.application_consumed_contract_names[app_key]
      intra_contract_name    = try(aci_contract.application_intra[app_key].name, null)
      external_subnets       = local.applications[app_key].external_subnets
    }
  }
}

output "contract_rules_in" {
  description = "Inbound (provided contract) subject, filter, and entry names."
  value = {
    for rule_key, subject in aci_contract_subject.application_in :
    rule_key => {
      subject      = subject.name
      filter       = aci_filter.application_in[rule_key].name
      filter_entry = aci_filter_entry.application_in[rule_key].name
    }
  }
}

output "contract_rules_out" {
  description = "Outbound (consumed contract) subject, filter, and entry names."
  value = {
    for rule_key, subject in aci_contract_subject.application_out :
    rule_key => {
      subject      = subject.name
      filter       = aci_filter.application_out[rule_key].name
      filter_entry = aci_filter_entry.application_out[rule_key].name
    }
  }
}
