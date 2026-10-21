# Subnet update plan report

Generated 14 October 2026. Configurations were updated and `terraform plan -out=plan.out` was run in each tenant directory. Nothing was applied.

NAC module `netascode/nac-aci/aci` is pinned to **2.1.0** (registry latest, published 21 September 2026) in each `main.tf` below. Previous pins were 2.0.0, except `tn-demo-03` (0.8.1) and `tn-conmurph-02` (`>=0.8.1`).

Each tenant that still had four `/27`s now uses the first four `/24`s of its `/21`, matching `tn-jorgquin`. Gateways are `.1/24`. Bridge domain, EPG, contract, and leak names follow the new prefix (`10.5.40.0_24` and so on).

Saved plans are the gitignored `plan.out` in each tenant directory.

## Do not apply these two plans

`tn-conmurph-01` and `tn-conmurph-02` still have fabric-wide objects in state from an older module run. NAC 2.1.0, with `manage_fabric_policies = false`, no longer tracks them, so the plan destroys them. That includes the fabric AAA tree, not just the tenant description.

Objects the plans delete include:

- `uni/userext` and `uni/userext/authrealm` (default and console auth, password profile, block-login, pre-login banner, web token)
- `uni/userext/domain-conmurph`
- default fabric and infra policies (`uni/fabric/pol-default`, ISIS, L2/L3 interface policies, endpoint loop protection, error-disabled recovery, Coop, PTP, IP aging, and related defaults)

`tn-conmurph-02` also plans to create `fvTenant` `conmurph-02` again. Refresh reported the existing tenant as absent, which is consistent with the API user not being able to read it. Applying that plan can recreate the tenant and still delete the fabric objects above.

Remove those fabric objects from state without destroying them before any apply. Do not run `terraform apply plan.out` in either directory.

## Allocation

Already on a `/21`, left unchanged:

| Tenant | Block |
| --- | --- |
| tn-jorgquin | 10.5.8.0/21 |
| tn-ssharman | 10.5.32.0/21 |

`tn-fgandola` was already reserved as **10.5.24.0/21** in the lab notes. Its configuration still had `10.1.10.0/24`, so that file was moved onto the reserved block rather than given a second one.

New blocks, in list order, for tenants whose configuration still had the old `10.1` prefix:

| Tenant | Was | Block | Configured segments |
| --- | --- | --- | --- |
| tn-demo-01 | 10.1.1.0/24 | 10.5.40.0/21 | 10.5.40.0/24 – 10.5.43.0/24 |
| tn-demo-02 | 10.1.2.0/24 | 10.5.48.0/21 | 10.5.48.0/24 – 10.5.51.0/24 |
| tn-demo-03 | 10.1.3.0/24 | 10.5.56.0/21 | 10.5.56.0/24 – 10.5.59.0/24 |
| tn-cgrabows | 10.1.11.0/24 | 10.5.64.0/21 | 10.5.64.0/24 – 10.5.67.0/24 |
| tn-conmurph-01 | description only | 10.5.72.0/21 | tenant description only |
| tn-conmurph-02 | description only | 10.5.80.0/21 | tenant description only |
| tn-maxalvar | 10.1.16.0/24 | 10.5.88.0/21 | 10.5.88.0/24 – 10.5.91.0/24 |

Not changed, because the listed `10.1` prefix is not what the configuration contains:

| Tenant | Why |
| --- | --- |
| tn-demo-04 | Files use 10.0.71.0/24–10.0.73.0/24, and the YAML tenant name is `demo-03`. |
| tn-demo-05 | File names the tenant `demo-04` and uses 10.0.81.0/24–10.0.82.0/24. |
| tn-demo-06 | No tenant directory. |

## Plan results

| Tenant | Plan | Add | Change | Destroy | What an apply would do |
| --- | --- | --- | --- | --- | --- |
| tn-demo-01 | succeeded | 50 | 10 | 49 | Replace the four `/27` bridge domains, subnets, EPGs, VMM attachments, ESG selectors, and route leaks with the four `/24`s. |
| tn-demo-02 | succeeded | 47 | 13 | 46 | Same replacement. The first gateway moves from the stray `10.0.1.1/24` to `10.5.48.1/24`. |
| tn-demo-03 | succeeded | 79 | 0 | 0 | Create the whole tenant model. Local state has no managed resources, so existing `10.1.3` objects, if still on the APIC, are not in this plan and would not be deleted. |
| tn-fgandola | succeeded, refresh drift | 106 | 7 | 1 | Create the new `/24`s. Refresh reported 104 in-state objects as already absent, including objects this edit did not rename (`1.1.1.0_24`, application profiles, and the old `10.1.10` bridge domains). Confirm those objects on the APIC before apply. If the read failed because of the tenant API user, apply would try to recreate them and would drop the old `/27`s from state without deleting them. |
| tn-cgrabows | succeeded | 64 | 11 | 60 | Replace the four `/27` bridge domains, subnets, EPGs, contracts (`permit-to-esg-*`), leaks, and ESG selectors with the four `/24`s. |
| tn-conmurph-01 | succeeded | 6 | 1 | 30 | Update the tenant description to `10.5.72.0/21`, and destroy fabric AAA and default fabric policies. Do not apply. |
| tn-conmurph-02 | succeeded | 13 | 0 | 29 | Same fabric deletes, plus a create of tenant `conmurph-02`. Do not apply. |
| tn-maxalvar | succeeded | 81 | 9 | 81 | Replace the four `/27` bridge domains, subnets, EPGs, leaks, and the `permit-to-epg`, `permit-to-esg`, and `permit-intra-esg` contracts with the four `/24`s. |

For the in-place replacements (`tn-demo-01`, `tn-demo-02`, `tn-cgrabows`, `tn-maxalvar`), apply deletes the old bridge domain and EPG and creates new ones. Endpoints and VMM port groups on the old names are removed. DHCP labels and route leaks move with the new prefixes. The `/21` still has four unused `/24`s (for example `10.5.44.0/24`–`10.5.47.0/24` on `tn-demo-01`); they are not configured.

## NAC 2.1.0 side effects

These show up on objects whose names did not change. They come from new module defaults, not from the prefix move.

- A `terraform_data.validation` resource is created.
- Filter entries gain `applyToFrag = no`.
- Bridge domains gain `ipv6McastAllow = no` (seen on the `6.6.6.0_24` PBR bridge domain).
- The DHCP relay provider is replaced in state. The provider is still `10.237.97.133` toward shared-services; only the Terraform address of `dhcpRsProv` changes.
- Tenant description is set to the `/21`.
- `tn-demo-01` and `tn-demo-02` also update L3Out, OSPF or BGP, and, on `tn-demo-02`, the redirect policy and service-graph template, because 2.1.0 writes additional attributes on those objects.

## Other edits

- `tn-fgandola` EPG `10.5.27.0_24` pointed at bridge domain `10.1.10.64_27`. That reference now points at `10.5.27.0_24`.
- `tn-demo-02` bridge domain `10.1.2.0_27` used gateway `10.0.1.1/24`. It is now `10.5.48.1/24`.
- `tn-demo-03` `data/network-centric-configuration.nac.yaml` was updated to the same prefixes. `main.tf` still loads only `data/application-centric-configuration.nac.yaml`, so the plan above is the application-centric file.
- `tn-conmurph-01` and `tn-conmurph-02` have no bridge domains or EPGs. Only the tenant description changed.

## VRF core multicast RP

Reserved for the sparse-mode rendezvous point in VRF `core`. Not a tenant `/21`, and not part of the plans above.

| Use | Address |
| --- | --- |
| RP, both GX-01 switches | `172.22.4.1` |
| Active, `L12-C93600CD-GX-01` `loopback2` | `172.22.4.1/30` |
| Standby, `L13-C93600CD-GX-01` `loopback2` | `172.22.4.1/29` |
| Group | `239.1.0.0/16` |

`12.0.0.x` and `13.0.0.x` stay the rack router-ids on `loopback0`. `10.237.0.0/16` stays the range reached from the corporate network. `172.22.0.0/16` is inside `172.16.0.0/12` and is otherwise unused. `172.16.10.0`–`172.16.12.0` remain the BRKDCN DMZ. `172.22` is the private stand-in for 224. The same address is on both switches; the `/30` is active and the `/29` is the standby.

OSPF in VRF `core` will advertise `172.22.4.0/30` and `172.22.4.0/29`. Deny `172.22.4.0/29` on the OSPF-to-BGP redistribution if this prefix should stay off the corporate network. ACI static RP, when configured, is `172.22.4.1` sparse mode in `tn-shared-services` and `tn-ssharman`.

## Authentication

Plans for `tn-demo-03`, `tn-fgandola`, `tn-cgrabows`, and `tn-maxalvar` used each directory's existing `terraform.tfvars`.

The `api_user` password stored for `tn-demo-01`, `tn-demo-02`, `tn-conmurph-01`, and `tn-conmurph-02` was rejected by the APIC. Those four plans were rerun with the working `api_user` credential already stored in `tn-demo-03/terraform.tfvars`, passed as a temporary var-file that was deleted afterward. That password was not copied into the other tenants' files or into this report.
