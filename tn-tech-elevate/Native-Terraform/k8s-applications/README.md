# k8s-applications

Terraform stack for onboarding Kubernetes applications into ACI tenant `tn-tech-elevate`.

## Objects created

For each entry in `k8s_applications`:

- Application Profile: `k8s.ns.<namespace>.<application_name>`
- ESG: `<application_name>`
- App ESG provides contract: `permit-to-k8s.ns.<namespace>.<application_name>`
- App ESG consumes external provided contracts (default: `uni/tn-tech-elevate/brc-permit-to-all-external-subnets`)
- External ESGs consume app provided contract (default consumer ESG: `uni/tn-tech-elevate/ap-external-subnets/esg-all-external-subnets`)
- ESG optional intra contract reference: `permit-intra-k8s.ns.<namespace>.<application_name>` (when enabled per app)
- ESG external subnet selectors: `ip=='<cidr>'` for each CIDR in `external_subnets`

For each contract rule direction under an application:

- Contract Subject: `<subject>` (`TCP`, `UDP`, `ICMP`, `Redirect`)
- Provided contract filter: `k8s.ns.<namespace>.<application_name>-<subject-lower>-in-src-<src>-dst-<dst>`
- Consumed contract filter: `k8s.ns.<namespace>.<application_name>-<subject-lower>-out-src-<src>-dst-<dst>`
- Filter Entry: `<subject-lower>-src-<src>-dst-<dst>`
- Filter entry `stateful` defaults to enabled (`yes`) and can be disabled per rule.

Example:

- Contract: `permit-to-k8s.ns.ssharman.sock-shop`
- Consumed Contract: `permit-from-k8s.ns.ssharman.sock-shop`
- Intra Contract (optional): `permit-intra-k8s.ns.ssharman.sock-shop`
- Subject: `TCP`
- Source port: `any`
- Destination port: `443`
- Provided filter: `k8s.ns.ssharman.sock-shop-tcp-in-src-any-dst-443`
- Consumed filter: `k8s.ns.ssharman.sock-shop-tcp-out-src-any-dst-443`
- Filter entry: `tcp-src-any-dst-443`

## Name length safeguards (APIC)

APIC naming properties for these objects are constrained, so this stack enforces safe name handling:

- Contract, Application Profile, Filter, and Filter Entry names are capped at `64` characters.
- If a generated name exceeds `64`, it is shortened deterministically with an 8-char SHA1 suffix.
- This keeps names APIC-compatible while preserving uniqueness.

## Inputs

Required:

- `apic_username`
- `apic_password`
- `apic_url`
- `vrf_name`

Optional:

- `tenant_name` (default: `tn-tech-elevate`)
- `contract_prefix` (default: `permit-to`)
- `consumed_contract_prefix` (default: `permit-from`)
- `intra_contract_prefix` (default: `permit-intra`)
- `contract_scope` (default fallback for provided/consumed: `context`, valid: `context`, `tenant`, `global`)
- `default_provided_contract_consumer_esg_dns` (default: `["uni/tn-tech-elevate/ap-external-subnets/esg-all-external-subnets"]`)
- `default_consumed_contract_provider_dns` (default: `["uni/tn-tech-elevate/brc-permit-to-all-external-subnets"]`)
- `k8s_applications_yaml_file` (default: `k8s-applications.yaml`)

`k8s_applications` can be supplied directly in tfvars, or loaded from YAML via `k8s_applications_yaml_file`.

Recommended auto-loaded variable files:

- `k8s-applications.auto.tfvars` for non-secret stack settings (tenant, VRF, prefixes, YAML path)
- `apic.credentials.auto.tfvars` for APIC credentials

With those files present, `terraform plan` and `terraform apply` work without `-var-file`.

## YAML structure

Use `k8s-applications.yaml`:

```yaml
k8s_applications:
  sock-shop:
    namespace: ssharman
    application_name: sock-shop
    enable_intra_esg_contract: true
    provided_contract_scope: context # optional override
    consumed_contract_scope: tenant  # optional override
    provided_contract_consumer_esg_dns: # optional override
      - uni/tn-tech-elevate/ap-external-subnets/esg-all-external-subnets
    consumed_contract_provider_dns: # optional override
      - uni/tn-tech-elevate/brc-permit-to-all-external-subnets
    external_subnets:
      - 10.10.10.10/32
    contract_rules_in:
      - subject: TCP
        source_port: "any"
        destination_port: "443"
        stateful: true
        # Optional, created by another plan:
        # service_graph: "uni/tn-tech-elevate/AbsGraph-your-graph"
    contract_rules_out:
      - subject: TCP
        source_port: "any"
        destination_port: "8443"
        stateful: true
  dns-cache:
    namespace: shared-services
    application_name: dns
    external_subnets:
      - 10.30.40.10/32
    contract_rules_in:
      - subject: UDP
        source_port: "any"
        destination_port: "53"
        stateful: true
        # service_graph: "uni/tn-tech-elevate/AbsGraph-dns-service-graph"
    contract_rules_out:
      - subject: UDP
        source_port: "any"
        destination_port: "53"
        stateful: true
        # service_graph: "uni/tn-tech-elevate/AbsGraph-dns-service-graph"
```

Allowed subject values are:

- `TCP`
- `UDP`
- `ICMP`
- `Redirect`

## APIC credentials source

Store APIC credentials in a local-only tfvars file:

- `apic.credentials.auto.tfvars`

This file is gitignored in this folder and should not be committed.

Example content:

```hcl
apic_username = "api_user"
apic_password = "replace_me"
apic_url      = "https://apic.example.local"
```

## Scale and lifecycle

Add an app by adding a new key under `k8s_applications`.

Remove an app by deleting its key from `k8s_applications`.

Terraform will create/update/destroy only the related ACI objects for that app.
