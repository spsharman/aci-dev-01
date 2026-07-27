# Deliver Secure Data Center Demos that Back the Perfect Pitch (TEIL06)

This demo environment allows the attendee to migrate a customer network from an insecure "open" Data Center Network, to a secure Data Center Network with application security at the forefront. The lab leverages multiple different technologies to secure a number of different applications:

- ACI provides the secure network infrastructure
- Cisco Smart Switches provides stateful L3/4 security
- FTD provides stateful L3/7 security
- Cisco Secure Workload provides endpoint protection
- Isovalent/Cilium provides Kubernetes security
- Nexus Dashboard provides application visibility and compliance
- Splunk provides a centralised logging and analysis platform for the entire environment

The lab heavily leverages Cisco's [Network as Code](https://netascode.cisco.com/) to fully automate the network changes that increase the security of the network. A number of configuration files are leveraged within the lab to ensure consistent configuration, however the lab user will be required to manually implement the different security options. 

## Lab Tasks

The lab is broken into a number of different tasks that allows the lab user to gradually apply more security to the different applications which are running in the lab. The lab starts with a very typical customer design which is an insecure network containing a single VRF and leverages vzAny with a single permit any contract

![Current network topology](./images/section-1/image.png)