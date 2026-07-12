output "discovered_esg_names" {
  description = "ESG names discovered under the selected application profile in NAC YAML."
  value       = local.discovered_esg_names
}

output "managed_set_rule_names" {
  description = "Final set-rule names that Terraform will manage after exclusions."
  value       = keys(local.generated_set_rule_data)
}
