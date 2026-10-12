# Cut plan: ssharman vrf-01 L3Out to the smart switch

Date: 2026-10-11

Build a BGP L3Out in tenant `ssharman` on `vpc_to_smart-switch`, using the same shape as `isovalent` `vrf-03-bgp-svi` (VLAN 41, `10.100.6.24/29`, ACI AS 65254, smart switch AS 65255).

This L3Out is how `10.5.34.0/24` and `10.5.35.0/24` on the smart switch stay in `ssharman:vrf-01` with `10.5.32.0/24` and `10.5.33.0/24` on ACI. The default already leaked from shared-services is exported to the smart switch. Moved prefixes are leaked back into shared-services and advertised to the core as AS 64801.

Do not peer `tn-ssharman:vrf-01` to VRF `core`. That plan is the separate smart-switch cut sheet and is not part of this change.

## Addressing and AS

Last `/24` of `10.5.32.0/21` is the peering pool. `/29`s are taken from the bottom.

| Block | Use |
| --- | --- |
| `10.5.39.0/29` | This L3Out, smart switch |
| `10.5.39.8/29` | Reserved, core pod 1 |
| `10.5.39.16/29` | Reserved, core pod 2 |

`10.5.39.0/29`:

| Address | Use |
| --- | --- |
| `10.5.39.0` | Network |
| `10.5.39.1` | Leaf 1101 |
| `10.5.39.2` | Leaf 1102 |
| `10.5.39.3` | Shared |
| `10.5.39.4` | Smart switch `tn-ssharman:vrf-01` |
| `10.5.39.5`–`.6` | Spare |
| `10.5.39.7` | Broadcast |

| Side | AS |
| --- | --- |
| ACI L3Out `local_as` | **64811** |
| Smart switch VRF `local-as` | **65257** |

64811 is the next tenant AS after 64810. 65257 is the smart-switch side, the same pairing as 65254 / 65255. eBGP needs two AS numbers. 65253 stays the global BGP process on the smart switch. 64801 stays shared-services toward the core.

VLAN **48** on the existing vPC. VLAN 41 is `isovalent.vrf-03`. VLANs 46 and 47 are the host SVIs `10.5.34.1/24` and `10.5.35.1/24`.

Tenant **10**, VRF **01**. Router ID is `{leaf}.{leaf}.{tenant}.{vrf}`. Loopback is `{leaf}.{leaf}.{tenant}.{vrf}{address}` with address `.1`, so the last octet is `11`.

| Node | Router ID | Loopback |
| --- | --- | --- |
| 1101 | `110.1.10.1` | `110.1.10.11` |
| 1102 | `110.2.10.1` | `110.2.10.11` |
| 2101 | `210.1.10.1` | `210.1.10.11` |
| 2102 | `210.2.10.1` | `210.2.10.11` |

The SVI is only on the pod 1 vPC, same as VLAN 41. Pod 2 nodes are in the node profile so the VRF has router IDs there. They do not get a peering subnet.

## 1. Access policies

`access-policies/data/1_pools.nac.yaml`, new pool:

```yaml
      - name: ssharman.vrf-01
        allocation: static
        ranges:
          - from: 48
            description: L3out SVI ssharman.vrf-01 to Smart Switch
```

`access-policies/data/2_domains.nac.yaml`:

```yaml
      - name: ssharman.vrf-01
        vlan_pool: ssharman.vrf-01
```

`access-policies/data/3_policies.nac.yaml`, under `vlans-allowed-to-smart-switches` `routed_domains`, next to `isovalent.vrf-03`:

```yaml
          - ssharman.vrf-01
```

## 2. Tenant ssharman

Add under `policies`, following the `vrf-03-bgp-svi` policy set.

```yaml
        bgp_peer_prefix_policies:
          - name: smart-switch-bgp-prefix-policy
            description: BGP prefix policy for Smart Switch
            action: reject
            threshold: 75
            max_prefixes: 100

        bgp_timer_policies:
          - name: core-bgp-timers
            description: BGP timer policies for smart switch peering
            keepalive_interval: 60
            hold_interval: 180
            graceful_restart_helper: true
            maximum_as_limit: 10

        bfd_interface_policies:
          - name: smart-switch-bfd
            description: single-hop BFD for the smart switch SVI
            detection_multiplier: 3
            echo_admin_state: true
            echo_rx_interval: 50
            min_rx_interval: 50
            min_tx_interval: 50

        match_rules:
          - name: match-default-route
            description: exact match for default route 0.0.0.0/0
            prefixes:
              - ip: 0.0.0.0/0
                aggregate: false

          - name: match-vrf-01-subnets
            description: subnets still on ACI bridge domains
            prefixes:
              - ip: 10.5.32.0/24
                aggregate: false
              - ip: 10.5.33.0/24
                aggregate: false

        route_control_route_maps:
          - name: export-vrf-01-to-smart-switch
            type: global
            contexts:
              - name: export-vrf-01-subnets
                order: 0
                action: permit
                match_rules:
                  - match-vrf-01-subnets
              - name: export-default-route
                order: 1
                action: permit
                match_rules:
                  - match-default-route
```

`smart-switch-bfd` is the single-hop interface policy. NaC attaches it with `bfd_policy` on the logical interface profile. The BGP peer still needs `bfd: true`, which sets the peer control bit. Timers are 50 ms / multiplier 3 with echo on, the same defaults the smart switch uses when `bfd` is configured with no interval. This session is TTL 1, so a BFD multihop node policy is not used.

Add the L3Out. `import_route_control_enforcement: false` matches `vrf-03-bgp-svi`. The `network` statements on the smart switch are the prefixes it originates.

```yaml
      l3outs:
        - name: vrf-01-bgp-svi
          description: L3out SVI to Smart Switch BGP AS64811
          alias: vrf-01-to-smart-switch
          vrf: vrf-01
          domain: ssharman.vrf-01
          import_route_control_enforcement: false
          export_route_map:
            type: global
            contexts:
              - name: export-vrf-01-subnets
                order: 0
                action: permit
                match_rules:
                  - match-vrf-01-subnets
              - name: export-default-route
                order: 1
                action: permit
                match_rules:
                  - match-default-route

          node_profiles:
            - name: border-leafs
              nodes:
                - node_id: 1101
                  pod_id: 1
                  router_id: 110.1.10.1
                  router_id_as_loopback: false
                  loopbacks:
                    - 110.1.10.11
                - node_id: 1102
                  pod_id: 1
                  router_id: 110.2.10.1
                  router_id_as_loopback: false
                  loopbacks:
                    - 110.2.10.11
                - node_id: 2101
                  pod_id: 2
                  router_id: 210.1.10.1
                  router_id_as_loopback: false
                  loopbacks:
                    - 210.1.10.11
                - node_id: 2102
                  pod_id: 2
                  router_id: 210.2.10.1
                  router_id_as_loopback: false
                  loopbacks:
                    - 210.2.10.11
              bgp:
                timer_policy: core-bgp-timers
              interface_profiles:
                - name: vpc_to_smart-switch
                  bfd_policy: smart-switch-bfd
                  interfaces:
                    - node_id: 1101
                      node2_id: 1102
                      channel: vpc_to_smart-switch
                      mode: regular
                      scope: vrf
                      vlan: 48
                      svi: true
                      ip_a: 10.5.39.1/29
                      ip_b: 10.5.39.2/29
                      ip_shared: 10.5.39.3/29
                      mtu: 1500
                      bgp_peers:
                        - ip: 10.5.39.4
                          description: Smart Switch SVI
                          remote_as: 65257
                          local_as: 64811
                          allow_self_as: false
                          as_override: false
                          disable_peer_as_check: false
                          next_hop_self: true
                          send_community: false
                          send_ext_community: false
                          allowed_self_as_count: 3
                          bfd: true
                          disable_connected_check: false
                          ttl: 1
                          remove_all_private_as: false
                          remove_private_as: false
                          replace_private_as_with_local_as: false
                          unicast_address_family: true
                          multicast_address_family: false
                          admin_state: true
                          as_propagate: no-prepend
                          peer_prefix_policy: smart-switch-bgp-prefix-policy
                          export_route_control: export-vrf-01-to-smart-switch

          external_endpoint_groups:
            - name: dummy-extEPG-for-vrf-01-bgp-svi-AS-64811
              description: do not use - this is a placeholder to enable the L3out to be created for vrf-01-bgp-svi
```

The external EPG has no subnets and no contracts. That matches `dummy-extEPG-for-vrf-03-bgp-svi-AS-65254` on `isovalent`. ACI still requires an external EPG on the L3Out. Classification of the smart-switch prefixes is an external ESG under a new application profile, the same shape as `external-subnets-esgs` / `10.100.9.0_24`.

```yaml
      application_profiles:
        - name: external-subnets-esgs
          description: ESGs are used to define security groups
          endpoint_security_groups:
            - name: smart-switch-subnets
              vrf: vrf-01
              deployment_immediacy: immediate
              ip_external_subnet_selectors:
                - ip: 10.5.34.0/24
                  shared: true
                - ip: 10.5.35.0/24
                  shared: true
              contracts:
                consumers:
                  - network-security-groups-permit-to-all-epgs
                providers:
                  - network-security-groups-permit-from-all-epgs
```

`all-epgs` already provides `network-security-groups-permit-to-all-epgs` and consumes `network-security-groups-permit-from-all-epgs`. The external ESG is the other side of that pair. `10.5.32.0/24` and `10.5.33.0/24` are members of `all-epgs`.

On VRF `vrf-01`, replace the commented external leak so the core learns the moved prefixes through shared-services. Do not leak `10.5.39.0/29`. It is a transit subnet and is not meant to be reached from Cisco.

```yaml
          leaked_external_prefixes:
            - prefix: 10.5.34.0/24
              destinations:
                - tenant: shared-services
                  vrf: vrf-01
                  public: true
            - prefix: 10.5.35.0/24
              destinations:
                - tenant: shared-services
                  vrf: vrf-01
                  public: true
```

Leave the existing leaks of `10.5.32.0/24` and `10.5.33.0/24` in place. Update the tenant file header. It currently says the tenant has no local L3Out.

## 3. Smart switch

Global BGP process stays 65253. Nothing under the default VRF changes. VLAN 48 is an SVI in `tn-ssharman:vrf-01`. Vlan46 and Vlan47 stay the host gateways.

No prefix-lists or route-maps. `tn-isovalent.vrf-03` does not use them toward its L3Out either. ACI already filters what it sends with `export-vrf-01-to-smart-switch`. The `network` statements are the only prefixes this VRF originates, so an outbound route-map would match that same pair and nothing else.

```
vlan 48
  name ssharman-vrf-01-l3out

interface Vlan48
  description ACI ssharman vrf-01-bgp-svi AS64811
  no shutdown
  vrf member tn-ssharman:vrf-01
  ip address 10.5.39.4/29
  no ip redirects

router bgp 65253
  vrf tn-ssharman:vrf-01
    local-as 65257 no-prepend replace-as
    router-id 10.5.34.1
    address-family ipv4 unicast
      network 10.5.34.0/24
      network 10.5.35.0/24
      maximum-paths 2
    neighbor 10.5.39.1
      bfd
      remote-as 64811
      local-as 65257 no-prepend replace-as
      description ACI leaf 1101 L3out ssharman.vrf-01
      update-source Vlan48
      address-family ipv4 unicast
        next-hop-self
    neighbor 10.5.39.2
      bfd
      remote-as 64811
      local-as 65257 no-prepend replace-as
      description ACI leaf 1102 L3out ssharman.vrf-01
      update-source Vlan48
      address-family ipv4 unicast
        next-hop-self
```

The shared address `10.5.39.3` is not a BGP neighbor. ACI `next_hop_self` rewrites the routes to `.1` and `.2`.

## Out of scope

- Default-VRF BGP to ACI on Ethernet1/3 and Ethernet1/4
- `tn-isovalent.vrf-03` and VLAN 41
- `tn-ssharman:vrf-01-pbr` and VLAN 45
- A core L3Out for tenant `ssharman`
- Advertising `10.5.32.0/21`

## Validation

On the smart switch:

```
show ip bgp summary vrf tn-ssharman:vrf-01
show ip route vrf tn-ssharman:vrf-01
show bgp vrf tn-ssharman:vrf-01 ipv4 unicast neighbors 10.5.39.1 advertised-routes
show bgp vrf tn-ssharman:vrf-01 ipv4 unicast neighbors 10.5.39.1 routes
ping 10.5.39.1 vrf tn-ssharman:vrf-01 source 10.5.39.4
ping 10.5.39.2 vrf tn-ssharman:vrf-01 source 10.5.39.4
```

Expect both neighbors Established, AS 64811. Advertised routes are only `10.5.34.0/24` and `10.5.35.0/24`. Received routes are `0.0.0.0/0`, `10.5.32.0/24`, and `10.5.33.0/24`, each with two paths via `10.5.39.1` and `10.5.39.2`.

On leaf 1101 or 1102, in tenant `ssharman` VRF `vrf-01`:

```
show ip route vrf ssharman:vrf-01 10.5.34.0/24
show ip route vrf ssharman:vrf-01 10.5.35.0/24
show bgp ipv4 unicast vrf ssharman:vrf-01 summary
```

The two `/24`s are BGP from `10.5.39.4`. The default in that VRF still points at shared-services.

On L12 (`10.237.96.212`), VRF `core`:

```
show bgp vrf core ipv4 unicast 10.5.34.0/24
show bgp vrf core ipv4 unicast 10.5.35.0/24
```

Both are AS path 64801, via `110.1.1.11` and `110.2.1.11`. `10.5.39.0/29` must not appear. `10.5.32.0/24` and `10.5.33.0/24` stay on that same 64801 path.

From a host on `10.5.34.0/24`, ping a host on `10.5.32.0/24`. The forward path is the smart switch to leaf 1101 or 1102, then the bridge domain. It does not cross the core.

Confirm existing sessions did not move:

```
show ip bgp summary
show ip bgp summary vrf tn-isovalent.vrf-03
```

## Rollback

Remove the smart-switch BGP neighbors and Vlan48. Remove the L3Out, the external ESG `smart-switch-subnets`, the external leak, and the new route-control and BFD policies from tenant `ssharman`. Remove routed domain `ssharman.vrf-01` from the AAEP, then the domain and VLAN pool. Leave the shared-services leaks of `10.5.32.0/24` and `10.5.33.0/24` as they are.
