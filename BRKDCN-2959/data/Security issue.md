# Security issue

## Consumer Tenant

shared-service:vrf-01       scope: 2457601
shared-service:vrf-01       classID: 5475
extEPG - all-ext-subnets    pcTag: 5476
extEPG - lab-desktops       pcTag: 5481

Client IP matches pcTag 5481 (lab-dekstops)

## Provider Tenant

BRKDCN-2959:vrf-01          scope: 2097155
BRKDCN-2959:vrf-01          classID: 16386
ESG                         pcTag: 5485

Provider IP matches pcTag 5485 (ESG)

## Contract in place from extEPG 5475 <> ESG 5485 - no connectivity as expected

### The zoning rules are from the Provider VRF. 

There is a contract from shared-services:vrf-01 all-ext-subnets to BRKDCN-2959:vrf-01 application-01:all-services. The consumer **cannot** reach the provider as there is a more specific extEPG scope.

aci-dev-01-apic-01# fabric 1101-1102 show zoning-rule scope 2097155
----------------------------------------------------------------
 Node 1101 (aci-dev-01-pod-01-leaf-1101)
----------------------------------------------------------------
+---------+--------+--------+----------+----------------+---------+---------+---------------------------------------------------+-----------------+------------------------+
| Rule ID | SrcEPG | DstEPG | FilterID |      Dir       |  operSt |  Scope  |                        Name                       |      Action     |        Priority        |
+---------+--------+--------+----------+----------------+---------+---------+---------------------------------------------------+-----------------+------------------------+
|   4432  |  5476  |  5485  | default  |     bi-dir     | enabled | 2097155 | BRKDCN-2959:permit-to-application-01-all-services |      permit     |     src_dst_any(9)     |
|   4448  |  5485  |  5476  | default  | uni-dir-ignore | enabled | 2097155 | BRKDCN-2959:permit-to-application-01-all-services |      permit     |     src_dst_any(9)     |
|   4453  |   0    | 49154  | implicit |    uni-dir     | enabled | 2097155 |                                                   |      permit     |     src_dst_any(9)     |
|   4437  |   10   |   0    | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |    class-eq-deny(2)    |
|   4162  |   0    |   10   | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |    class-eq-deny(2)    |
|   4466  |  5476  |   0    | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    | shsrc_any_any_deny(12) |
|   4178  |   0    |   15   | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |  any_vrf_any_deny(22)  |
|   4177  |   0    |   0    | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |    any_any_any(21)     |
|   4292  |   0    |   0    | implarp  |    uni-dir     | enabled | 2097155 |                                                   |      permit     |   any_any_filter(17)   |
|   4271  |  5485  |   14   | implicit |    uni-dir     | enabled | 2097155 |                                                   | permit_override |     src_dst_any(9)     |
|   4430  |   0    |  5476  | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    | shsrc_any_any_deny(12) |
+---------+--------+--------+----------+----------------+---------+---------+---------------------------------------------------+-----------------+------------------------+

----------------------------------------------------------------
 Node 1102 (aci-dev-01-pod-01-leaf-1102)
----------------------------------------------------------------
+---------+--------+--------+----------+----------------+---------+---------+---------------------------------------------------+-----------------+------------------------+
| Rule ID | SrcEPG | DstEPG | FilterID |      Dir       |  operSt |  Scope  |                        Name                       |      Action     |        Priority        |
+---------+--------+--------+----------+----------------+---------+---------+---------------------------------------------------+-----------------+------------------------+
|   4195  |  5476  |  5485  | default  |     bi-dir     | enabled | 2097155 | BRKDCN-2959:permit-to-application-01-all-services |      permit     |     src_dst_any(9)     |
|   4430  |  5485  |  5476  | default  | uni-dir-ignore | enabled | 2097155 | BRKDCN-2959:permit-to-application-01-all-services |      permit     |     src_dst_any(9)     |
|   4249  |   0    |   15   | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |  any_vrf_any_deny(22)  |
|   4158  |   0    |   0    | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |    any_any_any(21)     |
|   4443  |   0    |   0    | implarp  |    uni-dir     | enabled | 2097155 |                                                   |      permit     |   any_any_filter(17)   |
|   4432  |   0    | 49154  | implicit |    uni-dir     | enabled | 2097155 |                                                   |      permit     |     src_dst_any(9)     |
|   4467  |   0    |   10   | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |    class-eq-deny(2)    |
|   4309  |   10   |   0    | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |    class-eq-deny(2)    |
|   4193  |  5485  |   14   | implicit |    uni-dir     | enabled | 2097155 |                                                   | permit_override |     src_dst_any(9)     |
|   4462  |   0    |  5476  | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    | shsrc_any_any_deny(12) |
|   4243  |  5476  |   0    | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    | shsrc_any_any_deny(12) |
+---------+--------+--------+----------+----------------+---------+---------+---------------------------------------------------+-----------------+------------------------+

## Contract in place from extEPG 5481 <> ESG 5485 - connectivity working as expected

The zoning rules are from the Provider VRF. 

There is a contract from shared-services:vrf-01 all-lab-desktops to BRKDCN-2959:vrf-01 application-01:all-services. The consumer **can** reach the provider as the source IP matches the more specific extEPG scope.

aci-dev-01-apic-01# fabric 1101-1102 show zoning-rule scope 2097155
----------------------------------------------------------------
 Node 1101 (aci-dev-01-pod-01-leaf-1101)
----------------------------------------------------------------
+---------+--------+--------+----------+----------------+---------+---------+---------------------------------------------------+-----------------+------------------------+
| Rule ID | SrcEPG | DstEPG | FilterID |      Dir       |  operSt |  Scope  |                        Name                       |      Action     |        Priority        |
+---------+--------+--------+----------+----------------+---------+---------+---------------------------------------------------+-----------------+------------------------+
|   4448  |  5485  |   14   | implicit |    uni-dir     | enabled | 2097155 |                                                   | permit_override |     src_dst_any(9)     |
|   4432  |   0    |  5481  | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    | shsrc_any_any_deny(12) |
|   4466  |  5481  |   0    | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    | shsrc_any_any_deny(12) |
|   4271  |  5485  |  5481  | default  | uni-dir-ignore | enabled | 2097155 | BRKDCN-2959:permit-to-application-01-all-services |      permit     |     src_dst_any(9)     |
|   4430  |  5481  |  5485  | default  |     bi-dir     | enabled | 2097155 | BRKDCN-2959:permit-to-application-01-all-services |      permit     |     src_dst_any(9)     |
|   4453  |   0    | 49154  | implicit |    uni-dir     | enabled | 2097155 |                                                   |      permit     |     src_dst_any(9)     |
|   4437  |   10   |   0    | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |    class-eq-deny(2)    |
|   4162  |   0    |   10   | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |    class-eq-deny(2)    |
|   4178  |   0    |   15   | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |  any_vrf_any_deny(22)  |
|   4177  |   0    |   0    | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |    any_any_any(21)     |
|   4292  |   0    |   0    | implarp  |    uni-dir     | enabled | 2097155 |                                                   |      permit     |   any_any_filter(17)   |
+---------+--------+--------+----------+----------------+---------+---------+---------------------------------------------------+-----------------+------------------------+

----------------------------------------------------------------
 Node 1102 (aci-dev-01-pod-01-leaf-1102)
----------------------------------------------------------------
+---------+--------+--------+----------+----------------+---------+---------+---------------------------------------------------+-----------------+------------------------+
| Rule ID | SrcEPG | DstEPG | FilterID |      Dir       |  operSt |  Scope  |                        Name                       |      Action     |        Priority        |
+---------+--------+--------+----------+----------------+---------+---------+---------------------------------------------------+-----------------+------------------------+
|   4430  |  5485  |   14   | implicit |    uni-dir     | enabled | 2097155 |                                                   | permit_override |     src_dst_any(9)     |
|   4195  |   0    |  5481  | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    | shsrc_any_any_deny(12) |
|   4193  |  5485  |  5481  | default  | uni-dir-ignore | enabled | 2097155 | BRKDCN-2959:permit-to-application-01-all-services |      permit     |     src_dst_any(9)     |
|   4243  |  5481  |   0    | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    | shsrc_any_any_deny(12) |
|   4462  |  5481  |  5485  | default  |     bi-dir     | enabled | 2097155 | BRKDCN-2959:permit-to-application-01-all-services |      permit     |     src_dst_any(9)     |
|   4249  |   0    |   15   | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |  any_vrf_any_deny(22)  |
|   4158  |   0    |   0    | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |    any_any_any(21)     |
|   4443  |   0    |   0    | implarp  |    uni-dir     | enabled | 2097155 |                                                   |      permit     |   any_any_filter(17)   |
|   4432  |   0    | 49154  | implicit |    uni-dir     | enabled | 2097155 |                                                   |      permit     |     src_dst_any(9)     |
|   4467  |   0    |   10   | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |    class-eq-deny(2)    |
|   4309  |   10   |   0    | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |    class-eq-deny(2)    |
+---------+--------+--------+----------+----------------+---------+---------+---------------------------------------------------+-----------------+------------------------+

## Contract in place from extEPG 5476 <> ESG 5485, plus vzAny configured as consumer in the provider VRF - this allows the external client to reach the provider even though the extEPG does not match the client pcTag

The zoning rules are from the Provider VRF. 

There is a contract from shared-services:vrf-01 all-ext-subnets to BRKDCN-2959:vrf-01 application-01:all-services. 

This should **not** work as the contract is applied to the incorrect consumer extEPG, however if the provider VRF consumes the contract with vzAny, connectivity is allowed from the consumer to the provider despite the source IP matching the incorrect extEPG.

aci-dev-01-apic-01# fabric 1101-1102 show zoning-rule scope 2097155
----------------------------------------------------------------
 Node 1101 (aci-dev-01-pod-01-leaf-1101)
----------------------------------------------------------------
+---------+--------+--------+----------+----------------+---------+---------+---------------------------------------------------+-----------------+------------------------+
| Rule ID | SrcEPG | DstEPG | FilterID |      Dir       |  operSt |  Scope  |                        Name                       |      Action     |        Priority        |
+---------+--------+--------+----------+----------------+---------+---------+---------------------------------------------------+-----------------+------------------------+
|   4432  |  5476  |  5485  | default  |     bi-dir     | enabled | 2097155 | BRKDCN-2959:permit-to-application-01-all-services |      permit     |     src_dst_any(9)     |
|   4448  |  5485  |  5476  | default  | uni-dir-ignore | enabled | 2097155 | BRKDCN-2959:permit-to-application-01-all-services |      permit     |     src_dst_any(9)     |
|   4464  |  5485  |   0    | default  | uni-dir-ignore | enabled | 2097155 | BRKDCN-2959:permit-to-application-01-all-services |      permit     | shsrc_any_any_perm(11) |
|   4166  |   0    |  5485  | default  |     bi-dir     | enabled | 2097155 | BRKDCN-2959:permit-to-application-01-all-services |      permit     | shsrc_any_any_perm(11) |
|   4453  |   0    | 49154  | implicit |    uni-dir     | enabled | 2097155 |                                                   |      permit     |     src_dst_any(9)     |
|   4437  |   10   |   0    | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |    class-eq-deny(2)    |
|   4162  |   0    |   10   | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |    class-eq-deny(2)    |
|   4466  |  5476  |   0    | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    | shsrc_any_any_deny(12) |
|   4178  |   0    |   15   | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |  any_vrf_any_deny(22)  |
|   4177  |   0    |   0    | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |    any_any_any(21)     |
|   4292  |   0    |   0    | implarp  |    uni-dir     | enabled | 2097155 |                                                   |      permit     |   any_any_filter(17)   |
|   4271  |  5485  |   14   | implicit |    uni-dir     | enabled | 2097155 |                                                   | permit_override |     src_dst_any(9)     |
|   4430  |   0    |  5476  | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    | shsrc_any_any_deny(12) |
+---------+--------+--------+----------+----------------+---------+---------+---------------------------------------------------+-----------------+------------------------+

----------------------------------------------------------------
 Node 1102 (aci-dev-01-pod-01-leaf-1102)
----------------------------------------------------------------
+---------+--------+--------+----------+----------------+---------+---------+---------------------------------------------------+-----------------+------------------------+
| Rule ID | SrcEPG | DstEPG | FilterID |      Dir       |  operSt |  Scope  |                        Name                       |      Action     |        Priority        |
+---------+--------+--------+----------+----------------+---------+---------+---------------------------------------------------+-----------------+------------------------+
|   4195  |  5476  |  5485  | default  |     bi-dir     | enabled | 2097155 | BRKDCN-2959:permit-to-application-01-all-services |      permit     |     src_dst_any(9)     |
|   4430  |  5485  |  5476  | default  | uni-dir-ignore | enabled | 2097155 | BRKDCN-2959:permit-to-application-01-all-services |      permit     |     src_dst_any(9)     |
|   4414  |  5485  |   0    | default  | uni-dir-ignore | enabled | 2097155 | BRKDCN-2959:permit-to-application-01-all-services |      permit     | shsrc_any_any_perm(11) |
|   4466  |   0    |  5485  | default  |     bi-dir     | enabled | 2097155 | BRKDCN-2959:permit-to-application-01-all-services |      permit     | shsrc_any_any_perm(11) |
|   4249  |   0    |   15   | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |  any_vrf_any_deny(22)  |
|   4158  |   0    |   0    | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |    any_any_any(21)     |
|   4443  |   0    |   0    | implarp  |    uni-dir     | enabled | 2097155 |                                                   |      permit     |   any_any_filter(17)   |
|   4432  |   0    | 49154  | implicit |    uni-dir     | enabled | 2097155 |                                                   |      permit     |     src_dst_any(9)     |
|   4467  |   0    |   10   | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |    class-eq-deny(2)    |
|   4309  |   10   |   0    | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    |    class-eq-deny(2)    |
|   4193  |  5485  |   14   | implicit |    uni-dir     | enabled | 2097155 |                                                   | permit_override |     src_dst_any(9)     |
|   4462  |   0    |  5476  | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    | shsrc_any_any_deny(12) |
|   4243  |  5476  |   0    | implicit |    uni-dir     | enabled | 2097155 |                                                   |     deny,log    | shsrc_any_any_deny(12) |
+---------+--------+--------+----------+----------------+---------+---------+---------------------------------------------------+-----------------+------------------------+
