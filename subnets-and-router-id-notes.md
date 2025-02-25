# Deployment notes

## Lab local subnet allocation

10.0.0.0 IXN
10.1.0.0 ACI
10.2.0.0 Hyperfabric
10.3.0.0 VXLAN
10.4.0.0 K8's isovalent

## BGP AS numbers

65101 - VXLAN
64714 - dCloud
65090 - hyperfabric L09
65051 - aci-dev-01 overlay-1
65151 - aci-dev-01 isovalent:vrf-01
65160 - hyperfabric L16
65252 - isovalent k8s nodes
64800 - core
64801 - aci-dev-01 shared-services:vrf-01 

## VRF Route Distinguishers on core routers

VRF management: RD 64800:1
VRF core:       RD 64800:2
VRF ixn:        RD 64800:3

## Router IDs

## Node.Fabric.0.X

101.1.0.1 shared-services:vrf-01  Node-1101 BGP loopback 10.237.96.22/32 AS-64801
102.1.0.1 shared-services:vrf-01  Node-1102 BGP loopback 10.237.96.23/32 AS-64801
101.1.0.1 shared-services:vrf-01  Node-1101 OSPF loopback 10.237.96.27/32 AS-64801
102.1.0.1 shared-services:vrf-01  Node-1102 OSPF loopback 10.237.96.28/32 AS-64801

101.2.0.1 shared-services:vrf-01  Node-2101 BGP loopback 10.237.96.28/32 AS-64801
102.2.0.1 shared-services:vrf-01  Node-2102 BGP loopback 10.237.96.29/32 AS-64801

101.1.0.2 demo-01 Node-1101 OSPF Router ID as loopback
102.1.0.2 demo-01 Node-1102 OSPF Router ID as loopback

101.1.0.3 demo-02 Node-1101 OSPF Router ID as loopback
102.1.0.3 demo-02 Node-1102 OSPF Router ID as loopback

101.1.0.4 isovalent Node-1101 BGP Router ID as loopback
102.1.0.4 isovalent Node-1102 BGP Router ID as loopback
101.2.0.4 isovalent Node-2101 BGP Router ID as loopback
102.2.0.4 isovalent Node-2102 BGP Router ID as loopback
101.2.0.5 isovalent Node-2103 BGP Router ID as loopback
102.2.0.5 isovalent Node-2104 BGP Router ID as loopback

