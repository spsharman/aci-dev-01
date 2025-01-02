# Deployment notes

## Subnet allocation

10.0.0.0 IXN
10.1.0.0 ACI
10.2.0.0 Hyperfabric
10.3.0.0 VXLAN
10.4.0.0 K8's isovalent

## VRF Route Distinguishers on core routers

VRF management: RD 64800:0
VRF core:       RD 64800:1
VRF ixn:        RD 64800:2

## Router IDs

## Node.Fabric.0.X

101.1.0.1 shared-services:vrf-01  Node-1101 BGP loopback 10.237.96.22/32 AS-64801
102.1.0.1 shared-services:vrf-01  Node-1102 BGP loopback 10.237.96.23/32 AS-64801
101.1.0.1 shared-services:vrf-01  Node-1101 OSPF loopback 10.237.96.27/32 AS-64801
102.1.0.1 shared-services:vrf-01  Node-1102 OSPF loopback 10.237.96.28/32 AS-64801

101.1.0.2 demo-01 Node-1101 OSPF Router ID as loopback
102.1.0.2 demo-01 Node-1102 OSPF Router ID as loopback

101.1.0.3 demo-02 Node-1101 OSPF Router ID as loopback
102.1.0.3 demo-02 Node-1102 OSPF Router ID as loopback

101.1.0.4 isovalent Node-1101 BGP Router ID as loopback
102.1.0.4 isovalent Node-1102 BGP Router ID as loopback