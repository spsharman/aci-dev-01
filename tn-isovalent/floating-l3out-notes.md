# Notes

## Floating L3out - no secondary address on interface profile

```
aci-dev-01-apic-01# fabric 1101-1102 show ip int vrf isovalent:vrf-01
----------------------------------------------------------------
 Node 1101 (aci-dev-01-pod-01-leaf-1101)
----------------------------------------------------------------
IP Interface Status for VRF "isovalent:vrf-01"
vlan24, Interface status: protocol-up/link-up/admin-up, iod: 91, mode: pervasive
  IP address: 10.237.101.65, IP subnet: 10.237.101.64/28
  IP broadcast address: 255.255.255.255
  IP primary address route-preference: 0, tag: 0
vlan37, Interface status: protocol-up/link-up/admin-up, iod: 83, mode: external
  IP address: 10.237.101.1, IP subnet: 10.237.101.0/27
  IP address: 10.237.101.3, IP subnet: 10.237.101.0/27 secondary anchor-floating-ip
  IP broadcast address: 255.255.255.255
  IP primary address route-preference: 0, tag: 0
lo2, Interface status: protocol-up/link-up/admin-up, iod: 74, mode: unspecified
  IP address: 101.1.0.4, IP subnet: 101.1.0.4/32
  IP broadcast address: 255.255.255.255
  IP primary address route-preference: 0, tag: 0


----------------------------------------------------------------
 Node 1102 (aci-dev-01-pod-01-leaf-1102)
----------------------------------------------------------------
IP Interface Status for VRF "isovalent:vrf-01"
vlan21, Interface status: protocol-up/link-up/admin-up, iod: 91, mode: pervasive
  IP address: 10.237.101.65, IP subnet: 10.237.101.64/28
  IP broadcast address: 255.255.255.255
  IP primary address route-preference: 0, tag: 0
vlan35, Interface status: protocol-up/link-up/admin-up, iod: 83, mode: external
  IP address: 10.237.101.2, IP subnet: 10.237.101.0/27
  IP address: 10.237.101.3, IP subnet: 10.237.101.0/27 secondary anchor-floating-ip
  IP broadcast address: 255.255.255.255
  IP primary address route-preference: 0, tag: 0
lo10, Interface status: protocol-up/link-up/admin-up, iod: 80, mode: unspecified
  IP address: 102.1.0.4, IP subnet: 102.1.0.4/32
  IP broadcast address: 255.255.255.255
  IP primary address route-preference: 0, tag: 0
```

## Floating L3out - with secondary address 10.237.101.4/27 on interface profile

The secondary IP is pingable, however the anchor-floating-ip is not pingable.

```
aci-dev-01-apic-01# fabric 1101-1102 show ip int vrf isovalent:vrf-01
----------------------------------------------------------------
 Node 1101 (aci-dev-01-pod-01-leaf-1101)
----------------------------------------------------------------
IP Interface Status for VRF "isovalent:vrf-01"
vlan24, Interface status: protocol-up/link-up/admin-up, iod: 91, mode: pervasive
  IP address: 10.237.101.65, IP subnet: 10.237.101.64/28
  IP broadcast address: 255.255.255.255
  IP primary address route-preference: 0, tag: 0
vlan37, Interface status: protocol-up/link-up/admin-up, iod: 83, mode: external
  IP address: 10.237.101.1, IP subnet: 10.237.101.0/27
  IP address: 10.237.101.3, IP subnet: 10.237.101.0/27 secondary anchor-floating-ip
  IP address: 10.237.101.4, IP subnet: 10.237.101.0/27 secondary shared-ip
  IP broadcast address: 255.255.255.255
  IP primary address route-preference: 0, tag: 0
lo2, Interface status: protocol-up/link-up/admin-up, iod: 74, mode: unspecified
  IP address: 101.1.0.4, IP subnet: 101.1.0.4/32
  IP broadcast address: 255.255.255.255
  IP primary address route-preference: 0, tag: 0


----------------------------------------------------------------
 Node 1102 (aci-dev-01-pod-01-leaf-1102)
----------------------------------------------------------------
IP Interface Status for VRF "isovalent:vrf-01"
vlan21, Interface status: protocol-up/link-up/admin-up, iod: 91, mode: pervasive
  IP address: 10.237.101.65, IP subnet: 10.237.101.64/28
  IP broadcast address: 255.255.255.255
  IP primary address route-preference: 0, tag: 0
vlan35, Interface status: protocol-up/link-up/admin-up, iod: 83, mode: external
  IP address: 10.237.101.2, IP subnet: 10.237.101.0/27
  IP address: 10.237.101.3, IP subnet: 10.237.101.0/27 secondary anchor-floating-ip
  IP address: 10.237.101.4, IP subnet: 10.237.101.0/27 secondary shared-ip
  IP broadcast address: 255.255.255.255
  IP primary address route-preference: 0, tag: 0
lo10, Interface status: protocol-up/link-up/admin-up, iod: 80, mode: unspecified
  IP address: 102.1.0.4, IP subnet: 102.1.0.4/32
  IP broadcast address: 255.255.255.255
  IP primary address route-preference: 0, tag: 0
```

## Floating L3out - with secondary address 10.237.101.4/27 on interface profile, plus secondary address 10.237.101.5/27 on the floating path

```
aci-dev-01-apic-01# fabric 1101-1102 show ip int vrf isovalent:vrf-01
----------------------------------------------------------------
 Node 1101 (aci-dev-01-pod-01-leaf-1101)
----------------------------------------------------------------
IP Interface Status for VRF "isovalent:vrf-01"
vlan24, Interface status: protocol-up/link-up/admin-up, iod: 91, mode: pervasive
  IP address: 10.237.101.65, IP subnet: 10.237.101.64/28
  IP broadcast address: 255.255.255.255
  IP primary address route-preference: 0, tag: 0
vlan37, Interface status: protocol-up/link-up/admin-up, iod: 83, mode: external
  IP address: 10.237.101.1, IP subnet: 10.237.101.0/27
  IP address: 10.237.101.3, IP subnet: 10.237.101.0/27 secondary anchor-floating-ip
  IP address: 10.237.101.4, IP subnet: 10.237.101.0/27 secondary shared-ip
  IP address: 10.237.101.5, IP subnet: 10.237.101.0/27 secondary anchor-floating-ip
  IP broadcast address: 255.255.255.255
  IP primary address route-preference: 0, tag: 0
lo2, Interface status: protocol-up/link-up/admin-up, iod: 74, mode: unspecified
  IP address: 101.1.0.4, IP subnet: 101.1.0.4/32
  IP broadcast address: 255.255.255.255
  IP primary address route-preference: 0, tag: 0


----------------------------------------------------------------
 Node 1102 (aci-dev-01-pod-01-leaf-1102)
----------------------------------------------------------------
IP Interface Status for VRF "isovalent:vrf-01"
vlan21, Interface status: protocol-up/link-up/admin-up, iod: 91, mode: pervasive
  IP address: 10.237.101.65, IP subnet: 10.237.101.64/28
  IP broadcast address: 255.255.255.255
  IP primary address route-preference: 0, tag: 0
vlan35, Interface status: protocol-up/link-up/admin-up, iod: 83, mode: external
  IP address: 10.237.101.2, IP subnet: 10.237.101.0/27
  IP address: 10.237.101.3, IP subnet: 10.237.101.0/27 secondary anchor-floating-ip
  IP address: 10.237.101.4, IP subnet: 10.237.101.0/27 secondary shared-ip
  IP address: 10.237.101.5, IP subnet: 10.237.101.0/27 secondary anchor-floating-ip
  IP broadcast address: 255.255.255.255
  IP primary address route-preference: 0, tag: 0
lo10, Interface status: protocol-up/link-up/admin-up, iod: 80, mode: unspecified
  IP address: 102.1.0.4, IP subnet: 102.1.0.4/32
  IP broadcast address: 255.255.255.255
  IP primary address route-preference: 0, tag: 0
```