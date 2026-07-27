# Task 2

Task 2 involves migrating the current network topology from an EPG (Endpoint Group) based model to an ESG (Endpoint Security Group) model. This involves running a [Network as Code](https://netascode.cisco.com/) configuration plan to reconfigure the network. The configuration plan will be seamless to the application workloads as we are not applying any additional security at this point we are simply getting the network to a new baseline ready for additional security to be implemented.

## Why the migrate to an ESG model?

The ESG security model is the common model across Cisco's Data Center Network portfolio allowing interworking between ACI and NXOS networks via border gateways, and in the future Hyperfabric networks. A key benefit of the ESG security model is that Endpoint Security (IP/MAC) is detached from the Bridge Domain/VNI and is instead applied within a VRF.

## Step 1 - Migration to ESG security model

On the jumphost open vscode and navigate to the `Network-as-Code` folder, in the `/data` directory you will find a number of different configuration files.

Examine the high level differences between `00-base-network.nac.yaml` and `02-migrate-to-esgs.nac.yaml`

- In the left pane right click on `00-base-network.nac.yaml` and click `Select for Compare`
- In the left pane right click on `02-migrate-to-esgs.nac.yaml` and click `Compare with Selected`

Scroll through the compared files and note (at a high level) the various differences.

In summary the configuration `plan` will implement the following changes:

- create new external VRF (vrf-02)
- moves the current external L3out `vrf-01-static-route` to the new VRF (vrf-02)
- leaks a default route from vrf-02 (outside) to vrf-01 (inside)
- leaks directly attached subnets (Bridge Domains) from vrf-01 (inside) to vrf-02 (outside)
- leaks internally learned subnets (Kubernetes subnets) from vrf-01 (inside) to vrf-02 (outside)
- creates a single Endpoint Security Group (ESG) for all external endpoints
- creates a single Endpoint Security Group (ESG) for all Endpoint Groups (EPGs)
- creates a single Endpoint Security Group (ESG) for all Kubernetes (k8s) nodes
- creates a single Endpoint Security Group (ESG) for all Kubernetes (k8s) applications
- creates the following contracts with `permit-src-any-dst-any` filters:
  - epg-security-groups-permit-from-all-epgs
  - epg-security-groups-permit-to-all-epgs
  - k8s-nodes-permit-to-all-k8s-nodes
  - k8s-nodes-permit-from-all-k8s-nodes
  - k8s-applications-permit-from-all-k8s-applications
  - k8s-applications-permit-to-all-k8s-applications
- applies contracts to the external facing ESG on vrf-02
- retains the current vzAny contract on vrf-01 (inside) to preserve internal application connectivity

## Step 2 - Examine main.tf

In vscode select `main.tf` where you will note that there are a number of different configuration files that can be implemented. 

```
  yaml_files = ["data/00-base-network.nac.yaml"]
  # yaml_files = ["data/02-migrate-to-esgs.nac.yaml"]
  # yaml_files = ["data/04-add-service-nodes.nac.yaml"]
  # yaml_files = ["data/06-increase-contract-security.nac.yaml"]
```

- Remark out the line containing `00-base-network.nac.yaml`
- Unremark the line containing `02-migrate-to-esgs.nac.yaml`
- save the file

```
  # yaml_files = ["data/00-base-network.nac.yaml"]
  yaml_files = ["data/02-migrate-to-esgs.nac.yaml"]
  # yaml_files = ["data/04-add-service-nodes.nac.yaml"]
  # yaml_files = ["data/06-increase-contract-security.nac.yaml"]
```

Open a new vscode terminal window and plan the deployment using the command: `terraform plan`

!!! note "Network as Code"
    The Network as Code terraform code examines the current configuration and plans what changes are required to meet the desired state in the new `02-migrate-to-esgs.nac.yaml` plan.

Once the plan has completed apply it using the command: `terraform apply`

When prompted approve the changes with `yes`

## Step 3 - check application connectivity is unchanges

Open the Chrome browser on the jumphost and connect to the following applications:

- SIWAPP (https://siwapp.ip.address/) - VM hosted application
- Online Boutique (https://online-boutique.ip.address/) - VM hosted application
- Hubble (https://hubble.ip.address/) - K8s hosted application
- Juice Shop (https://juice-shop.ip.address/) - K8s hosted application

### Key Takeways

The fabric design was migrated from a simple insecure design to a new design with split VRFs. External connectivity was moved from the internal VRF to the external VRF meaning that vzAny can continue to be used internally (vrf-01) without risking unintended connectivity from the outside to the different applications, instead external connectivity is allowed through explicit contracts and internal communication is allowed through vzAny. 

This is the first step foundational step to a more secure network. Security has been increased through the instantiation of a new external VRF, but the rules (source and destination ports) have remained open. 

This approach is critical to ensure that there cannot be any impact to application connectivity. 