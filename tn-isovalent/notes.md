# L3out Deployment Notes

If you configure nodes (i.e. without node profile) NAC copies the L3out name to both the node profile name, and interface profile name. 

A secondary address **does not** get configured for a port channel interface with a floating L3out.

## Examples

The following code takes the L3out name and uses it to create the node profiles and two interfaces profiles. The interface profiles identify each interface of the vPC. The secondary (shared) IP address **does** get created.

```
      l3outs:
        - name: isovalent.vrf-01-bgp-AS-65152
          description: L3out SVI with one node profile and two interface profiles
          alias: external-vrf
          vrf: vrf-01
          domain: isovalent.vrf-01

          nodes:
            - node_id: 1101
              router_id: 101.2.1.1
              interfaces:
                - channel: vpc_to_isovalent-node-01
                  mode: regular
                  vlan: 16
                  svi: true
                  ip: 10.237.101.1/27
                  ip_shared: 10.237.101.4/27
                  mtu: 1500

            - node_id: 1102
              router_id: 102.2.1.1
              interfaces:
                - channel: vpc_to_isovalent-node-01
                  mode: regular
                  vlan: 16
                  svi: true
                  ip: 10.237.101.2/27
                  ip_shared: 10.237.101.4/27
                  mtu: 1500
```

The following code takes the L3out name and uses it to create the node profiles and one interface profile. The interface profiles identifies both interfaces of the vPC. The secondary (shared) IP address **does** get created.

```
      l3outs:
        - name: isovalent.vrf-01-bgp-AS-65152
          description: L3out SVI with one node profile and one interface profile
          alias: external-vrf
          vrf: vrf-01
          domain: isovalent.vrf-01

          nodes:
            - node_id: 1101
              router_id: 101.2.1.1

            - node_id: 1102
              router_id: 101.2.1.1

              interfaces:
                - node_id: 1101
                  node2_id: 1102
                  channel: vpc_to_isovalent-node-01
                  mode: regular
                  vlan: 16
                  svi: true
                  ip_a: 10.237.101.1/27
                  ip_b: 10.237.101.2/27
                  ip_shared: 10.237.101.4/27
```

The following code takes the L3out name and uses it to create two node profiles, however the secondary (shared) IP address **does not** get created.

```
      l3outs:
        - name: isovalent.vrf-01-bgp-AS-65152
          description: L3out floating SVI with one node profile and two interface profiles
          alias: external-vrf
          vrf: vrf-01
          domain: isovalent.vrf-01

          nodes:
            - node_id: 1101
              router_id: 101.2.1.1
              interfaces:
                - node_id: 1101
                  channel: vpc_to_isovalent-node-01
                  mode: regular
                  vlan: 16
                  svi: false
                  ip: 10.237.101.1/27
                  ip_shared: 10.237.101.4/27
                  floating_svi: true
                  paths:
                    - floating_ip: 10.237.101.3/27
                      physical_domain: isovalent-nodes

            - node_id: 1102
              router_id: 101.2.1.1
              interfaces:
                - node2_id: 1102
                  channel: vpc_to_isovalent-node-01
                  mode: regular
                  vlan: 16
                  svi: false
                  ip: 10.237.101.2/27
                  ip_shared: 10.237.101.4/27
                  floating_svi: true
                  paths:
                    - floating_ip: 10.237.101.3/27
                      physical_domain: isovalent-nodes
```


The following code uses specific node profile and interface profile names, it creates one interface profile and the interface profiles identifies both interfaces of the vPC. The secondary (shared) IP address **does** get created.

```
      l3outs:
        - name: isovalent.vrf-01-bgp-AS-65152
          description: L3out SVI with one node profile and one interface profile
          alias: external-vrf
          vrf: vrf-01
          domain: isovalent.vrf-01

          node_profiles:
            - name: border-leafs
              nodes:
                - node_id: 1101
                  router_id: 101.2.1.1
                  
                - node_id: 1102
                  router_id: 102.2.1.1

              interface_profiles:
                - name: vpc_to_isovalent-node-01
                  interfaces:
                    - node_id: 1101
                      node2_id: 1102
                      channel: vpc_to_isovalent-node-01
                      mode: regular
                      vlan: 16
                      svi: true
                      ip_a: 10.237.101.1/27
                      ip_b: 10.237.101.2/27
                      ip_shared: 10.237.101.4/27
                      mtu: 1500
```

The following code uses specific node profile and interface profile names, it creates two interface profiles and the interface profiles identifies both interfaces of the vPC. The secondary (shared) IP address **does** get created.

```
      l3outs:
        - name: isovalent.vrf-01-bgp-AS-65152
          description: L3out SVI with one node profile and two interface profiles
          alias: external-vrf
          vrf: vrf-01
          domain: isovalent.vrf-01

          node_profiles:
            - name: border-leafs
              nodes:
                - node_id: 1101
                  router_id: 101.2.1.1
                  
                - node_id: 1102
                  router_id: 102.2.1.1

              interface_profiles:
                - name: vpc_to_isovalent-node-01
                  interfaces:
                    - node_id: 1101
                      channel: vpc_to_isovalent-node-01
                      mode: regular
                      vlan: 16
                      svi: true
                      ip: 10.237.101.1/27
                      ip_shared: 10.237.101.4/27
                      mtu: 1500

                    - node_id: 1102
                      channel: vpc_to_isovalent-node-01
                      mode: regular
                      vlan: 16
                      svi: true
                      ip: 10.237.101.2/27
                      ip_shared: 10.237.101.4/27
                      mtu: 1500
```

The following code uses specific node profile and interface profile names, it creates two interface profiles and the interface profiles. The secondary (shared) IP address **does not** get created.

```
      l3outs:
        - name: isovalent.vrf-01-bgp-AS-65152
          description: L3out floating SVI with one node profile and two interface profiles
          alias: external-vrf
          vrf: vrf-01
          domain: isovalent.vrf-01

          node_profiles:
            - name: border-leafs
              nodes:
                - node_id: 1101
                  router_id: 101.2.1.1
                  
                - node_id: 1102
                  router_id: 102.2.1.1

              interface_profiles:
                - name: vpc_to_isovalent-node-01
                  interfaces:
                    - node_id: 1101
                      channel: vpc_to_isovalent-node-01
                      mode: regular
                      vlan: 16
                      floating_svi: true
                      paths:
                        - floating_ip: 10.237.101.3/27
                          physical_domain: isovalent-nodes
                      ip: 10.237.101.1/27
                      ip_shared: 10.237.101.4/27
                      mtu: 1500

                    - node_id: 1102
                      channel: vpc_to_isovalent-node-01
                      mode: regular
                      vlan: 16
                      floating_svi: true
                      paths:
                        - floating_ip: 10.237.101.3/27
                          physical_domain: isovalent-nodes
                      ip: 10.237.101.2/27
                      ip_shared: 10.237.101.4/27
                      mtu: 1500
```