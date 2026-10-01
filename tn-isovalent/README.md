[![Terraform Version](https://img.shields.io/badge/terraform-%5E1.3-blue)](https://www.terraform.io)

# Nexus-as-Code - Simple example for ACI

This example is part of the Cisco [*Nexus as Code*](https://cisco.com/go/nexusascode) project. Its goal is to allow users to instantiate network fabrics in minutes using an easy to use, opinionated data model. It takes away the complexity of having to deal with references, dependencies or loops. By completely separating data (defining variables) from logic (infrastructure declaration), it allows the user to focus on describing the intended configuration while using a set of maintained and tested Terraform Modules without the need to understand the low-level ACI object model. More information can be found here: <https://developer.cisco.com/docs/nexus-as-code/#!simple-example>.

## Run the Terraform

You will need the following credentials:

- Terraform state is stored in S3 in the `isovalent-demo` RunOn account.  Use `duo-sso` to refresh your credentials before you run the make targets
- APIC credentials.  You can create a static credentials file in `~/.apic/credentials` or supply the crednetials at runtime:

Example to create a static credentials file:

```
mkdir -p ~/.apic && chmod 700 ~/.apic
cat > ~/.apic/credentials <<'EOF'
APIC_USERNAME=johndoe
APIC_PASSWORD='xxxxxxxx'
APIC_URL='https://64.103.44.66/'
EOF
chmod 600 ~/.apic/credentials
```

Example to provide credentials at runtime:

`make init APIC_USERNAME=johndoe APIC_PASSWORD='xxxx' APIC_URL='https://64.103.44.66/'`

## Network connectivity tests

Install the test dependency into the Python environment used by Make, then run `make network-test`. In this workspace, use `../../.venv/bin/python -m pip install -r requirements-test.txt`; otherwise activate your virtual environment and install with `python3 -m pip install -r requirements-test.txt`. The target prefers the workspace `.venv` when present and falls back to `python3`.

The suite checks API reachability locally, from the jumphost's default route, and bound to each jumphost interface (`10.237.101.6` and `10.100.0.26`). Hostname-based API curls also exercise DNS resolution. Separate jumphost checks ping each lab DNS server from both interfaces, and Internet checks run using the default source and `10.100.0.26`. The jumphost SSH connection supports your normal SSH configuration or agent; set `NETWORK_SSH_BATCHMODE=yes` to disable interactive authentication prompts.

Override the jumphost, source, DNS server, or jumphost interface addresses with `make network-test NETWORK_JUMPHOST=user@host NETWORK_SOURCE_IP=10.100.0.26 NETWORK_DNS_SERVER_IPS=10.237.97.134,10.237.97.135 NETWORK_JUMPHOST_INTERFACE_IPS=10.237.101.6,10.100.0.26`.
