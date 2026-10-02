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
