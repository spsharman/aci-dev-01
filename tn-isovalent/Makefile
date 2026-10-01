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

NETWORK_JUMPHOST ?= localuser@10.237.101.6
NETWORK_SOURCE_IP ?= 10.100.0.26
NETWORK_DNS_SERVER_IPS ?= 10.237.97.134,10.237.97.135
NETWORK_JUMPHOST_INTERFACE_IPS ?= 10.237.101.6,10.100.0.26
NETWORK_SSH_BATCHMODE ?= no
PYTHON ?= $(if $(wildcard ../../.venv/bin/python),../../.venv/bin/python,python3)

.PHONY: init plan apply destroy network-test

init:
	terraform init

plan:
	@$(LOAD_CREDS) terraform plan

apply:
	@$(LOAD_CREDS) terraform apply

destroy:
	@$(LOAD_CREDS) terraform destroy

network-test:
	NETWORK_JUMPHOST="$(NETWORK_JUMPHOST)" \
	NETWORK_SOURCE_IP="$(NETWORK_SOURCE_IP)" \
	NETWORK_DNS_SERVER_IPS="$(NETWORK_DNS_SERVER_IPS)" \
	NETWORK_JUMPHOST_INTERFACE_IPS="$(NETWORK_JUMPHOST_INTERFACE_IPS)" \
	NETWORK_SSH_BATCHMODE="$(NETWORK_SSH_BATCHMODE)" \
	$(PYTHON) -m pytest -v tests/network