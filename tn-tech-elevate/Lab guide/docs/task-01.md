# Task 1

Task 1 involves understanding the current network topology and building blocks. 

## Step 1 - Discover the current topology

Using the Chrome browser navigate to [APIC](https://apic.ip.address/) and select your tenant (need the tenant name structure)

- On the left menu tree open Networking > VRFs note there is a single VRF
  - Click `EPG|ESG Collection for the VRF` note there is a single provided and contract `intra-vrf`

Examine the protocols/ports that are allowed by the `intra-vrf` contract:

- On the left menu open Contracts > Standard
  - Click the `intra-vrf` contract and click the ">" to open the contract and show the `subject`
  - Click the subject `permit-src-any-dst-any` and note that it has a single filter `src-any-dst-any`

Examine the filter to understand what the Filter allows:

- On the left menu open Contracts > Filters
  - Click the `src-any-dst-any` filter and click the ">" to open the filter and show the `filter entry`
  - Click the filter entry `src-any-dst-any` and note that the EtherType is `Unspecified` - this allows all protocols/ports

- Collpase the Contracts folder in the left menu
- Collapse the VRFs folder in the left menu

Examine the SVIs (Bridge Domains) to understand which subnets are configured on the VRF:

- On the left menu open Networking > Bridge Domains
  - Click the `10.5.0.0_24` Bridge Domain and in the right hand pane note the VRF ID that the Bridge Domain is mapped to
  - Click the ">" to open the Bridge Domain, click the ">" to open the `Subnets`
  - Click the Subnet entry `10.5.0.1/24` and note that the IP address - this is the SVI that is created on the Bridge Domain

!!! info "A Bridge Domain is a VNI"

    A Bridge Domain is a VXLAN VNI that leverages an auto generated VXLAN segment ID. Which knowing the VNI ID is not required for ACI operation it is exposed in the UI

    - Click the `10.5.0.0_24` Bridge Domain
    - Click Advanced/Troubleshooting on the right hand pane
    - Identify the segment ID - this is the VXLAN ID

- Collpase the Bridge Domains folder in the left menu

Examine the L3out routed connections to the outside and to the Kubernetes (K8s) environment:

- On the left menu open Networking > L3Outs
  - Click the `vrf-01-static-route` L3out
  - Click all the ">" to open all the sub folders under the L3out
  - Click `border-leafs` and in the right pane double click `node-101` to show the static route that has been configured
  - Click the Logical Interface Profile `interfaces-to-csr1kv` and in the right pane click the `Floating L3out` to display the Interface IP addresses and VLAN used to peer to the csr1kv
  - Click `all-external-subnets` under External EPGs
  - Click `Policy` in the right pane and note the configured subnets

!!! info "An External EPG identifies remote workloads"

    The External EPG subnets control the classification of external endpoints. Subnets 0.0.0.0/1 and 128.0.0.0/1 identify all remote IP addresses and assign them to the External EPG security group (extEPG)

  - Click `Contracts` in the right pane and note that there are no contracts configured

!!! info "Why are no contracts configured to the outside?"

    The VRF is providing and consuming the same contract under `EPG|ESG Collection for the VRF`, this contract is therefore applied to all EPGs and extEPGs on the fabric allowing open communication. Whilst this is a simple deployment model the use of vzAny is insecure by design from a security perspective as it applies to everything on the VRF

  - Click the `vrf-01-bgp-AS-64808` L3out - this is the L3out that peers with the Kubernetes environment
  - Click all the ">" to open all the sub folders under the L3out
  - Click `BGP Peer` under the `k8s-nodes` under the Logical Interface Profiles
  - In the right hand pane note the `Remote AS number` - this is AS used by the K8s nodes, ACI will learn routes from this AS number
  - In the right hand pane note the `Local AS number` - this is AS used by ACI which the K8s nodes use for peering

Examine how the workloads are attached to the network:

- Collapse all configuration folders by click the middle icon (ladder icon) in the left pane

- On the left menu open the Tenant > Application Profiles > `workload-connectivity`
  - Click the ">" to open the `workload-connectivity` folder
  - Click the ">" to open `Application EPGs` folder
  - Click the first EPG `10.5.0.0_24`
  - In the right hand pan click `Policy` > `General`
  - Identify the Bridge Domain that the EPG is attached to - note the Bridge Domain to VRF relationship that was previously discovered
  - In the right hand pane click `Operational` and note the workloads that are attached to this network segment
  - Identify the `encap` VLANs - these are the VLANs that the workloads are attached too
  - Click the ">" to open the EPG `10.5.0.0_24` folder
  - Click `Domains (VMs and Bare-Metals)
  - In the right hand pane identify the `Domain` that this EPG is bound to

![Current network topology](./images/section-1/image.png)

## Step 2 - check application connectivity

Open the Chrome browser on the jumphost and connect to the following applications:

- SIWAPP (https://siwapp.ip.address/) - VM hosted application
- Online Boutique (https://online-boutique.ip.address/) - VM hosted application
- Hubble (https://hubble.ip.address/) - K8s hosted application
- Juice Shop (https://juice-shop.ip.address/) - K8s hosted application

### Key Takeways

The current fabric design whilst simple to deploy is insecure by design. There is a single contract which is applied (Provided and Consumed) to vzAny on the VRF, this contract encompasses all the EPGs and extEPGs that are attached to the VRF allowing open communication. 