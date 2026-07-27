# Task 3

Task 3 involves is the first step to add more security into the network 

## Step 1 - Add security devices

On the jumphost open vscode and navigate to the `Network-as-Code` folder, in the `/data` directory you will find a number of different configuration files.

Examine the high level differences between `02-base-network.nac.yaml` and `04-migrate-to-esgs.nac.yaml`

- In the left pane right click on `02-base-network.nac.yaml` and click `Select for Compare`
- In the left pane right click on `04-migrate-to-esgs.nac.yaml` and click `Compare with Selected`

Scroll through the compared files and note (at a high level) the various differences.

In summary the configuration `plan` will implement the following changes:

- add a FTD and associated policies for L3/7 North/South security
- add a FTD and associated policies for L3/7 East/West security
- add a Smart Switch and associated policies for L3/4 East/West stateful security
- applies a Service Graph to the smart switch (with an open policy) via the vzAny contract for stateful control of traffic on vrf-01

## Step 2 - Examine main.tf

In vscode select `main.tf` where you will note that there are a number of different configuration files that can be implemented. 

```
  # yaml_files = ["data/00-base-network.nac.yaml"]
  yaml_files = ["data/02-migrate-to-esgs.nac.yaml"]
  # yaml_files = ["data/04-add-service-nodes.nac.yaml"]
  # yaml_files = ["data/06-increase-contract-security.nac.yaml"]
```

- Remark out the line containing `02-migrate-to-esgs.nac.yaml`
- Unremark the line containing `04-add-service-nodes.nac.yaml`
- save the file

```
  # yaml_files = ["data/00-base-network.nac.yaml"]
  # yaml_files = ["data/02-migrate-to-esgs.nac.yaml"]
  yaml_files = ["data/04-add-service-nodes.nac.yaml"]
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

This is the second step to a more secure network. A smart switch has been added to the intra VRF contract on the internal VRF (vrf-01) to provide the option of stateful control.

**Note** at this point the Smart Switch rules are `permit-any-any log`, this approach allows the Smart Switch to have visibility (and log) all East/West traffic, however as the rules are open there will be no impact to traffic.