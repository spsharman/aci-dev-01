# Optional shell file with APIC_USERNAME / APIC_PASSWORD / APIC_URL.
# Precedence: make vars / env (e.g. `make plan APIC_URL=...`) > CREDS_FILE > TF_VAR_apic_* > variables.tf defaults.
CREDS_FILE ?= $(HOME)/.apic/credentials

export APIC_USERNAME APIC_PASSWORD APIC_URL

define LOAD_CREDS
if [ -f "$(CREDS_FILE)" ]; then \
  u="$${APIC_USERNAME}"; p="$${APIC_PASSWORD}"; l="$${APIC_URL}"; \
  set -a; . "$(CREDS_FILE)"; set +a; \
  [ -z "$$u" ] || APIC_USERNAME="$$u"; \
  [ -z "$$p" ] || APIC_PASSWORD="$$p"; \
  [ -z "$$l" ] || APIC_URL="$$l"; \
fi; \
[ -z "$${APIC_USERNAME}" ] || export TF_VAR_apic_username="$${APIC_USERNAME}"; \
[ -z "$${APIC_PASSWORD}" ] || export TF_VAR_apic_password="$${APIC_PASSWORD}"; \
[ -z "$${APIC_URL}" ] || export TF_VAR_apic_url="$${APIC_URL}";
endef

.PHONY: init plan apply destroy

init:
	terraform init

plan:
	@$(LOAD_CREDS) terraform plan

apply:
	@$(LOAD_CREDS) terraform apply

destroy:
	@$(LOAD_CREDS) terraform destroy