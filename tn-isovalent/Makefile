APIC_USERNAME ?= $(TF_VAR_apic_username)
APIC_PASSWORD ?= $(TF_VAR_apic_password)
APIC_URL ?= $(TF_VAR_apic_url)

export TF_VAR_apic_username := $(APIC_USERNAME)
export TF_VAR_apic_password := $(APIC_PASSWORD)
export TF_VAR_apic_url := $(APIC_URL)

.PHONY: check-vars init plan apply destroy

check-vars:
	@missing=""; \
	[ -n "$${TF_VAR_apic_username}" ] || missing="$$missing APIC_USERNAME"; \
	[ -n "$${TF_VAR_apic_password}" ] || missing="$$missing APIC_PASSWORD"; \
	[ -n "$${TF_VAR_apic_url}" ] || missing="$$missing APIC_URL"; \
	if [ -n "$$missing" ]; then \
		printf 'Error: missing required Terraform settings:%s\n' "$$missing" >&2; \
		printf 'Set these as Make variables or TF_VAR_apic_* environment variables.\n' >&2; \
		exit 2; \
	fi

init: check-vars
	terraform init

plan: check-vars
	terraform plan

apply: check-vars
	terraform apply

destroy: check-vars
	terraform destroy