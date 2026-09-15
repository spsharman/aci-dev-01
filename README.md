# aci-dev-01

Personal ACI lab notes and a small tenant-diagram tool. This is a **pet project**, not a Cisco product, and not official Cisco sample code.

There is **no support** and no SLA. Issues and questions may go unanswered.

## Tenant diagrams

`diagrams/render_v9_tenant_diagram.py` draws tenant / VRF / AP / ESG / contract PNGs from NAC YAML and/or APIC `tenant.json`.

APIC host, username, and password are **not** stored in this repository. Copy the example env file and keep the real values local:

```bash
cp diagrams/.env.example diagrams/.env
# edit diagrams/.env — that file is gitignored
```

Or export `APIC_HOST`, `APIC_USER`, and `APIC_PASS` in your shell. The password can also be typed in the dialog; it is never written to disk.

Run from the **repo root** (`aci-dev-01`), not from `diagrams/`.

### Four ways to run

1. Retrieve `tenant.json` from APIC

   `python3 diagrams/render_v9_tenant_diagram.py --no-prompt --tenant common --from-apic`

2. Path to a downloaded `tenant.json`

   `python3 diagrams/render_v9_tenant_diagram.py --no-prompt --tenant common --tenant-json diagrams/tn-common/tenant.json`

3. Retrieve from APIC plus NAC configuration

   `python3 diagrams/render_v9_tenant_diagram.py --no-prompt --tenant common --from-apic --nac path/to/configuration.nac.yaml`

4. Downloaded `tenant.json` plus NAC configuration

   `python3 diagrams/render_v9_tenant_diagram.py --no-prompt --tenant common --tenant-json diagrams/tn-common/tenant.json --nac path/to/configuration.nac.yaml`

With no flags, a prompt box asks for the same choices.

Outputs go to `diagrams/tn-<tenant>/`. A live query writes `tenant.json` there (also gitignored).

### Dependencies

```bash
python3 -m pip install pyyaml pillow
```

Lab APICs often use a self-signed certificate. This script skips TLS verification for that lab case only — do not copy that pattern to production.

## License

[MIT](LICENSE) — Copyright (c) 2026 Steve Sharman.

The license already disclaims all warranties. In addition: no support is offered, and this repository is not endorsed by Cisco or any employer. Use at your own risk, against your own lab, with your own credentials.
