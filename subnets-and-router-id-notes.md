# Deployment notes

## Lab local subnet allocation

- 10.0.0.0 IXN
- 10.1.0.0 ACI DEV 01 Infra
  - 10.1.0.0/16 ACI DEV 01 Pod 1 TEP Pool VRF overlay-1
  - 10.2.0.0/16 ACI DEV 01 Pod 2 TEP Pool VRF overlay-1
- 10.1.1.0 ACI DEV 01
  - 10.1.1.0/27 tn-demo-01
  - 10.1.1.32/27 tn-demo-01
  - 10.1.1.64/27 tn-demo-01
  - 10.1.1.96/27 tn-demo-01
- 10.1.2.0 ACI DEV 01
  - 10.1.2.0/27 tn-demo-02
  - 10.1.2.32/27 tn-demo-02
  - 10.1.2.64/27 tn-demo-02
  - 10.1.2.96/27 tn-demo-02
- 10.1.3.0 ACI DEV 01
  - 10.1.3.0/27 tn-demo-03
  - 10.1.3.32/27 tn-demo-03
  - 10.1.3.64/27 tn-demo-03
  - 10.1.3.96/27 tn-demo-03
- 10.1.4.0 ACI DEV 01
  - 10.1.4.0/27 tn-demo-04
  - 10.1.4.32/27 tn-demo-04
  - 10.1.4.64/27 tn-demo-04
  - 10.1.4.96/27 tn-demo-04
- 10.1.5.0 ACI DEV 01
  - 10.1.5.0/27 tn-demo-05
  - 10.1.5.32/27 tn-demo-05
  - 10.1.5.64/27 tn-demo-05
  - 10.1.5.96/27 tn-demo-05
- 10.1.6.0 ACI DEV 01
  - 10.1.6.0/27 tn-demo-06
  - 10.1.6.32/27 tn-demo-06
  - 10.1.6.64/27 tn-demo-06
  - 10.1.6.96/27 tn-demo-06
- 10.1.10.0 ACI DEV 01
  - 10.1.10.0/27 tn-fgandola
  - 10.1.10.32/27 tn-fgandola
  - 10.1.10.64/27 tn-fgandola
  - 10.1.10.96/27 tn-fgandola
- 10.1.11.0 ACI DEV 01
  - 10.1.11.0/27 tn-cgrabows
  - 10.1.11.32/27 tn-cgrabows
  - 10.1.11.64/27 tn-cgrabows
  - 10.1.11.96/27 tn-cgrabows
- 10.1.12.0 ACI DEV 01
  - 10.1.12.0/27 tn-conmurph-01
  - 10.1.12.32/27 tn-conmurph-01
  - 10.1.12.64/27 tn-conmurph-01
  - 10.1.12.96/27 tn-conmurph-01
- 10.1.13.0 ACI DEV 01
  - 10.1.13.0/27 tn-conmurph-02
  - 10.1.13.32/27 tn-conmurph-02
  - 10.1.13.64/27 tn-conmurph-02
  - 10.1.13.96/27 tn-conmurph-02

- 10.2.0.0 Hyperfabric

- 10.3.0.0 VXLAN

- 10.4.0.0 K8's isovalent

## BGP AS numbers

- 65101 - VXLAN
- 64714 - dCloud
- 65090 - hyperfabric L09
- 65051 - aci-dev-01 overlay-1
- 65151 - aci-dev-01 isovalent:vrf-01
- 65160 - hyperfabric L16
- 65252 - isovalent k8s nodes
- 64800 - core
- 64801 - aci-dev-01 shared-services:vrf-01 
- 64802 - dCloud vPod

## VRF Route Distinguishers on core routers

- VRF management: RD 64800:1
- VRF core:       RD 64800:2
- VRF ixn:        RD 64800:3

## Router IDs

## Node.Fabric.0.X

- 101.1.0.1 shared-services:vrf-01  Node-1101 BGP loopback 10.237.96.22/32 AS-64801
- 102.1.0.1 shared-services:vrf-01  Node-1102 BGP loopback 10.237.96.23/32 AS-64801
- 101.1.0.1 shared-services:vrf-01  Node-1101 OSPF loopback 10.237.96.27/32 AS-64801
- 102.1.0.1 shared-services:vrf-01  Node-1102 OSPF loopback 10.237.96.28/32 AS-64801

- 101.2.0.1 shared-services:vrf-01  Node-2101 BGP loopback 10.237.96.28/32 AS-64801
- 102.2.0.1 shared-services:vrf-01  Node-2102 BGP loopback 10.237.96.29/32 AS-64801

- 101.1.0.2 demo-01 Node-1101 OSPF Router ID as loopback
- 102.1.0.2 demo-01 Node-1102 OSPF Router ID as loopback

- 101.1.0.3 demo-02 Node-1101 OSPF Router ID as loopback
- 102.1.0.3 demo-02 Node-1102 OSPF Router ID as loopback

- 101.1.0.4 isovalent Node-1101 BGP Router ID as loopback
- 102.1.0.4 isovalent Node-1102 BGP Router ID as loopback
- 101.2.0.4 isovalent Node-2101 BGP Router ID as loopback
- 102.2.0.4 isovalent Node-2102 BGP Router ID as loopback
- 101.2.0.5 isovalent Node-2103 BGP Router ID as loopback
- 102.2.0.5 isovalent Node-2104 BGP Router ID as loopback

