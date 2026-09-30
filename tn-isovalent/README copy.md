[![Terraform Version](https://img.shields.io/badge/terraform-%5E1.3-blue)](https://www.terraform.io)

# Nexus-as-Code - Simple example for ACI

This example is part of the Cisco [*Nexus as Code*](https://cisco.com/go/nexusascode) project. Its goal is to allow users to instantiate network fabrics in minutes using an easy to use, opinionated data model. It takes away the complexity of having to deal with references, dependencies or loops. By completely separating data (defining variables) from logic (infrastructure declaration), it allows the user to focus on describing the intended configuration while using a set of maintained and tested Terraform Modules without the need to understand the low-level ACI object model. More information can be found here: <https://developer.cisco.com/docs/nexus-as-code/#!simple-example>.

## Run the Terraform

Example:

```
export APIC_USERNAME=johndoe
export APIC_PASSWORD='xxxxxxxx'
export APIC_URL='https://64.103.44.66/'
export TF_HTTP_USERNAME=terraform
export TF_HTTP_PASSWORD='xxxxxxxxxx'
```
