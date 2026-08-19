# Zoning Rules

ESG 49 = online-boutique
ESG 10938 = external-subnets
ESG 5484 = ftd via redirect

## external-subnets (c) to online-boutique (p)

show zoning-rule
src = external-subnets
dst = online-boutique
+---------+--------+--------+----------+----------------+---------+---------+----------------------------------------------------------------------+------------------+------------------------+
| Rule ID | SrcEPG | DstEPG | FilterID |      Dir       |  operSt |  Scope  |                                 Name                                 |      Action      |        Priority        |
+---------+--------+--------+----------+----------------+---------+---------+----------------------------------------------------------------------+------------------+------------------------+
|   4434  | 10938  |   49   |   416    |    uni-dir     | enabled | 2293763 |  tech-elevate:zzz-online-boutique-permit-to-all-endpoints-tcp-flags  | redir(destgrp-2) |     fully_qual(7)      |
|   5499  | 10938  |   49   |   426    |    uni-dir     | enabled | 2293763 |  tech-elevate:zzz-online-boutique-permit-to-all-endpoints-tcp-flags  | redir(destgrp-2) |     fully_qual(7)      |
|   5286  | 10938  |   49   |   428    |    uni-dir     | enabled | 2293763 |  tech-elevate:zzz-online-boutique-permit-to-all-endpoints-tcp-flags  | redir(destgrp-2) |     fully_qual(7)      |
+---------+--------+--------+----------+----------------+---------+---------+----------------------------------------------------------------------+------------------+------------------------+

show rule-id
+---------+--------+--------+----------+---------+---------+---------+--------------------------------------------------------------------+------------------+---------------+---------+
| Rule ID | SrcEPG | DstEPG | FilterID |   Dir   |  operSt |  Scope  |                                Name                                |      Action      |    Priority   |  Intent |
+---------+--------+--------+----------+---------+---------+---------+--------------------------------------------------------------------+------------------+---------------+---------+
|   4434  | 10938  |   49   |   416    | uni-dir | enabled | 2293763 | tech-elevate:zzz-online-boutique-permit-to-all-endpoints-tcp-flags | redir(destgrp-2) | fully_qual(7) | install |
|   5499  | 10938  |   49   |   426    | uni-dir | enabled | 2293763 | tech-elevate:zzz-online-boutique-permit-to-all-endpoints-tcp-flags | redir(destgrp-2) | fully_qual(7) | install |
|   5286  | 10938  |   49   |   428    | uni-dir | enabled | 2293763 | tech-elevate:zzz-online-boutique-permit-to-all-endpoints-tcp-flags | redir(destgrp-2) | fully_qual(7) | install |
+---------+--------+--------+----------+---------+---------+---------+--------------------------------------------------------------------+------------------+---------------+---------+

show filter-id
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-----------+---------+-------+-------------+-------------+----------+
| FilterId |  Name | EtherT |    ArpOpc   | Prot | ApplyToFrag | Stateful |  SFromPort  |   SToPort   | DFromPort | DToPort |  Prio |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-----------+---------+-------+-------------+-------------+----------+
|   416    | 416_0 |   ip   | unspecified | tcp  |      no     |    no    | unspecified | unspecified |    http   |   http  | flags | unspecified | unspecified |   syn    |
|   426    | 426_0 |   ip   | unspecified | tcp  |      no     |    no    | unspecified | unspecified |    http   |   http  | flags | unspecified | unspecified |   est    |
|   428    | 428_0 |   ip   | unspecified | tcp  |      no     |    no    | unspecified | unspecified |    http   |   http  | flags | unspecified | unspecified |   fin    |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-----------+---------+-------+-------------+-------------+----------+

show service redir
===============================================================================================================================================================
LEGEND
TL: Threshold(Low)  |  TH: Threshold(High) |  HP: HashProfile  |  HG: HealthGrp  | BAC: Backup-Dest |  TRA: Tracking | RES: Resiliency | W: Weight
===============================================================================================================================================================
GrpID Name            destination                                                    HG-name                                                        BAC W   operSt   operStQual      TL  TH  HP  TRA RES
===== ====            ===========                                                    ==============                                                 === === =======  ============    === === === === ===
2     destgrp-2       dest-[6.6.6.10]-[vxlan-2293763]                                tech-elevate::ftdv-01-north-south                              N   1   enabled  no-oper-grp     0   0   sym yes no


## ftd (c) to online-boutique (p)

show zoning-rule
src = ftd
dst = online-boutique
+---------+--------+--------+----------+---------+---------+---------+----------------------------------------------------------------------+--------+----------------+
| Rule ID | SrcEPG | DstEPG | FilterID |   Dir   |  operSt |  Scope  |                                 Name                                 | Action |    Priority    |
+---------+--------+--------+----------+---------+---------+---------+----------------------------------------------------------------------+--------+----------------+
|   5484  |  5484  |   49   | default  |  bi-dir | enabled | 2293763 |  tech-elevate:zzz-online-boutique-permit-to-all-endpoints-tcp-flags  | permit | src_dst_any(9) |
+---------+--------+--------+----------+---------+---------+---------+----------------------------------------------------------------------+--------+----------------+

+---------+--------+--------+----------+---------+---------+---------+----------------------------------------------------------------------+--------+----------------+---------+
| Rule ID | SrcEPG | DstEPG | FilterID |  Dir    |  operSt |  Scope  |                                Name                                  | Action |    Priority    |  Intent |
+---------+--------+--------+----------+---------+---------+---------+----------------------------------------------------------------------+--------+----------------+---------+
|   5484  |  5484  |   49   | default  | bi-dir  | enabled | 2293763 | tech-elevate:zzz-online-boutique-permit-to-all-endpoints-tcp-flags   | permit | src_dst_any(9) | install |
+---------+--------+--------+----------+---------+---------+---------+----------------------------------------------------------------------+--------+----------------+---------+

+----------+-------+-------------+-------------+-------------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+
| FilterId |  Name |    EtherT   |    ArpOpc   |     Prot    | ApplyToFrag | Stateful |  SFromPort  |   SToPort   |  DFromPort  |   DToPort   | Prio  |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+-------+-------------+-------------+-------------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+
| default  |  any  | unspecified | unspecified | unspecified |      no     |    no    | unspecified | unspecified | unspecified | unspecified | def   | unspecified | unspecified |          |
+----------+-------+-------------+-------------+-------------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+


## online-boutique (c) to external-subnets (p)

show zoning-rule
src = online-boutique
dst = external-subnets
+---------+--------+--------+----------+---------+---------+---------+----------------------------------------------------------------------+------------------+---------------+
| Rule ID | SrcEPG | DstEPG | FilterID |   Dir   |  operSt |  Scope  |                                 Name                                 |      Action      |    Priority   |
+---------+--------+--------+----------+---------+---------+---------+----------------------------------------------------------------------+------------------+---------------+
|   5298  |   49   | 10938  |   444    | uni-dir | enabled | 2293763 |  tech-elevate:zzz-online-boutique-permit-to-all-endpoints-tcp-flags  | redir(destgrp-2) | fully_qual(7) |
+---------+--------+--------+----------+---------+---------+---------+----------------------------------------------------------------------+------------------+---------------+

show zoning-rule
+---------+--------+--------+----------+---------+---------+---------+--------------------------------------------------------------------+------------------+---------------+---------+
| Rule ID | SrcEPG | DstEPG | FilterID |   Dir   |  operSt |  Scope  |                                Name                                |      Action      |    Priority   |  Intent |
+---------+--------+--------+----------+---------+---------+---------+--------------------------------------------------------------------+------------------+---------------+---------+
|   5298  |   49   | 10938  |   444    | uni-dir | enabled | 2293763 | tech-elevate:zzz-online-boutique-permit-to-all-endpoints-tcp-flags | redir(destgrp-2) | fully_qual(7) | install |
+---------+--------+--------+----------+---------+---------+---------+--------------------------------------------------------------------+------------------+---------------+---------+

show filter-id
+----------+-------+--------+-------------+------+-------------+----------+-----------+---------+-------------+-------------+-------+-------------+-------------+----------+
| FilterId |  Name | EtherT |    ArpOpc   | Prot | ApplyToFrag | Stateful | SFromPort | SToPort |  DFromPort  |   DToPort   |  Prio |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+-------+--------+-------------+------+-------------+----------+-----------+---------+-------------+-------------+-------+-------------+-------------+----------+
|   444    | 444_0 |   ip   | unspecified | tcp  |      no     |    no    |    http   |   http  | unspecified | unspecified | flags | unspecified | unspecified |   ack    |
+----------+-------+--------+-------------+------+-------------+----------+-----------+---------+-------------+-------------+-------+-------------+-------------+----------+


## ftd (c) to external-subnets (p)
+---------+--------+--------+----------+----------------+---------+---------+----------------------------------------------------------------------+------------------+------------------------+
| Rule ID | SrcEPG | DstEPG | FilterID |      Dir       |  operSt |  Scope  |                                 Name                                 |      Action      |        Priority        |
+---------+--------+--------+----------+----------------+---------+---------+----------------------------------------------------------------------+------------------+------------------------+
|   5342  |  5484  | 10938  |   444    |    uni-dir     | enabled | 2293763 |  tech-elevate:zzz-online-boutique-permit-to-all-endpoints-tcp-flags  |      permit      |     fully_qual(7)      |
+---------+--------+--------+----------+----------------+---------+---------+----------------------------------------------------------------------+------------------+------------------------+

show filter-id
+----------+-------+--------+-------------+------+-------------+----------+-----------+---------+-------------+-------------+-------+-------------+-------------+----------+
| FilterId |  Name | EtherT |    ArpOpc   | Prot | ApplyToFrag | Stateful | SFromPort | SToPort |  DFromPort  |   DToPort   |  Prio |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+-------+--------+-------------+------+-------------+----------+-----------+---------+-------------+-------------+-------+-------------+-------------+----------+
|   444    | 444_0 |   ip   | unspecified | tcp  |      no     |    no    |    http   |   http  | unspecified | unspecified | flags | unspecified | unspecified |   ack    |
+----------+-------+--------+-------------+------+-------------+----------+-----------+---------+-------------+-------------+-------+-------------+-------------+----------+




### setup

| Direction    | Src pcTag | Dst pcTag | Dst Port | TCP Rules | Action   | Filter Priority |
| ------------ | --------- | --------- | -------- | --------- | -------- | --------------- |
| External→App | External  | App       | 443      | syn       | redirect | 1 (flags)       |
| External→App | External  | App       | 443      | est       | redirect | 1 (flags)       |
| External→App | External  | App       | 443      | fin       | redirect | 1 (flags)       |

Contract 1 Reflexive (redirect to FW1):
| Direction    | Src pcTag | Dst pcTag | Src Port | TCP Rules | Action   | Filter Priority |
| ------------ | --------- | --------- | -------- | --------- | -------- | --------------- |
| App→External | App       | External  | 443      | ack       | redirect | 1 (flags)       |

Contract 2 Forward (permit or redirect to FW2):
| Direction    | Src pcTag | Dst pcTag | Ports | TCP Rules | Action          | Filter Priority |
| ------------ | --------- | --------- | ----- | --------- | --------------- | --------------- |
| App→External | App       | External  | any   | (none)    | permit/redirect | 5 (proto)       |

Contract 2 Reflexive (permit or redirect to FW2):
| Direction    | Src pcTag | Dst pcTag | Ports | TCP Rules | Action          | Filter Priority |
| ------------ | --------- | --------- | ----- | --------- | --------------- | --------------- |
| External→App | External  | App       | any   | ack       | permit/redirect | 1 (flags)       |





#### single port

+---------+--------+--------+----------+----------------+---------+---------+----------------------------------------------------------------------+------------------+------------------------+
| Rule ID | SrcEPG | DstEPG | FilterID |      Dir       |  operSt |  Scope  |                                 Name                                 |      Action      |        Priority        |
+---------+--------+--------+----------+----------------+---------+---------+----------------------------------------------------------------------+------------------+------------------------+
|   5433  |   49   | 10938  |   444    |    uni-dir     | enabled | 2293763 | tech-elevate:zzz-online-boutique-permit-to-all-endpoints-tcp-flags   | redir(destgrp-2) |     fully_qual(7)      |
|   5525  | 10938  |   49   |   416    |    uni-dir     | enabled | 2293763 | tech-elevate:zzz-online-boutique-permit-to-all-endpoints-tcp-flags   | redir(destgrp-2) |     fully_qual(7)      |
|   5400  | 10938  |   49   |   426    |    uni-dir     | enabled | 2293763 | tech-elevate:zzz-online-boutique-permit-to-all-endpoints-tcp-flags   | redir(destgrp-2) |     fully_qual(7)      |
|   5500  | 10938  |   49   |   428    |    uni-dir     | enabled | 2293763 | tech-elevate:zzz-online-boutique-permit-to-all-endpoints-tcp-flags   | redir(destgrp-2) |     fully_qual(7)      |
|   5389  |  5484  |   49   | default  |     bi-dir     | enabled | 2293763 | tech-elevate:zzz-online-boutique-permit-to-all-endpoints-tcp-flags   |      permit      |     src_dst_any(9)     |
|   5535  |  5484  | 10938  |   444    |    uni-dir     | enabled | 2293763 | tech-elevate:zzz-online-boutique-permit-to-all-endpoints-tcp-flags   |      permit      |     fully_qual(7)      |
|   5484  |   49   |  5484  | default  | uni-dir-ignore | enabled | 2293763 | tech-elevate:zzz-online-boutique-permit-to-all-endpoints-tcp-flags   |      permit      |     src_dst_any(9)     |
+---------+--------+--------+----------+----------------+---------+---------+----------------------------------------------------------------------+------------------+------------------------+

+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-----------+---------+-------+-------------+-------------+----------+
| FilterId |  Name | EtherT |    ArpOpc   | Prot | ApplyToFrag | Stateful |  SFromPort  |   SToPort   | DFromPort | DToPort |  Prio |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-----------+---------+-------+-------------+-------------+----------+
|   416    | 416_0 |   ip   | unspecified | tcp  |      no     |    no    | unspecified | unspecified |    http   |   http  | flags | unspecified | unspecified |   syn    |
|   426    | 426_0 |   ip   | unspecified | tcp  |      no     |    no    | unspecified | unspecified |    http   |   http  | flags | unspecified | unspecified |   est    |
|   428    | 428_0 |   ip   | unspecified | tcp  |      no     |    no    | unspecified | unspecified |    http   |   http  | flags | unspecified | unspecified |   fin    |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-----------+---------+-------+-------------+-------------+----------+

+----------+-------+--------+-------------+------+-------------+----------+-----------+---------+-------------+-------------+-------+-------------+-------------+----------+
| FilterId |  Name | EtherT |    ArpOpc   | Prot | ApplyToFrag | Stateful | SFromPort | SToPort |  DFromPort  |   DToPort   |  Prio |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+-------+--------+-------------+------+-------------+----------+-----------+---------+-------------+-------------+-------+-------------+-------------+----------+
|   444    | 444_0 |   ip   | unspecified | tcp  |      no     |    no    |    http   |   http  | unspecified | unspecified | flags | unspecified | unspecified |   ack    |
+----------+-------+--------+-------------+------+-------------+----------+-----------+---------+-------------+-------------+-------+-------------+-------------+----------+


### Add return rule

+---------+--------+--------+----------+----------------+---------+---------+----------------------------------------------------------------------+------------------+------------------------+
| Rule ID | SrcEPG | DstEPG | FilterID |      Dir       |  operSt |  Scope  |                                 Name                                 |      Action      |        Priority        |
+---------+--------+--------+----------+----------------+---------+---------+----------------------------------------------------------------------+------------------+------------------------+
|   4505  |   49   | 10938  | default  |    uni-dir     | enabled | 2293763 | tech-elevate:zzz-online-boutique-permit-from-all-endpoints-tcp-flags |      permit      |     src_dst_any(9)     |
|   5487  | 10938  |   49   |   436    |    uni-dir     | enabled | 2293763 | tech-elevate:zzz-online-boutique-permit-from-all-endpoints-tcp-flags |      permit      |     fully_qual(7)      |
+---------+--------+--------+----------+----------------+---------+---------+----------------------------------------------------------------------+------------------+------------------------+

+----------+------+-------------+-------------+-------------+-------------+----------+-------------+-------------+-------------+-------------+------+-------------+-------------+----------+
| FilterId | Name |    EtherT   |    ArpOpc   |     Prot    | ApplyToFrag | Stateful |  SFromPort  |   SToPort   |  DFromPort  |   DToPort   | Prio |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+------+-------------+-------------+-------------+-------------+----------+-------------+-------------+-------------+-------------+------+-------------+-------------+----------+
| default  | any  | unspecified | unspecified | unspecified |      no     |    no    | unspecified | unspecified | unspecified | unspecified | def  | unspecified | unspecified |          |
+----------+------+-------------+-------------+-------------+-------------+----------+-------------+-------------+-------------+-------------+------+-------------+-------------+----------+

+----------+------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+
| FilterId | Name | EtherT |    ArpOpc   | Prot | ApplyToFrag | Stateful |  SFromPort  |   SToPort   |  DFromPort  |   DToPort   |  Prio |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+
|    39    | 39_0 |   ip   | unspecified | tcp  |      no     |    no    | unspecified | unspecified | unspecified | unspecified | proto | unspecified | unspecified |          |
+----------+------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+

+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+
| FilterId |  Name | EtherT |    ArpOpc   | Prot | ApplyToFrag | Stateful |  SFromPort  |   SToPort   |  DFromPort  |   DToPort   |  Prio |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+
|   436    | 436_0 |   ip   | unspecified | tcp  |      no     |    no    | unspecified | unspecified | unspecified | unspecified | flags | unspecified | unspecified |   ack    |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+







+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+
| FilterId |  Name | EtherT |    ArpOpc   | Prot | ApplyToFrag | Stateful |  SFromPort  |   SToPort   |  DFromPort  |   DToPort   |  Prio |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+
|   117    | 117_0 |   ip   | unspecified | tcp  |      no     |   yes    | unspecified | unspecified | unspecified | unspecified | proto | unspecified | unspecified |          |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+

+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+
| FilterId |  Name | EtherT |    ArpOpc   | Prot | ApplyToFrag | Stateful |  SFromPort  |   SToPort   |  DFromPort  |   DToPort   |  Prio |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+
|   118    | 118_0 |   ip   | unspecified | tcp  |      no     |   yes    | unspecified | unspecified | unspecified | unspecified | flags | unspecified | unspecified |   ack    |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+


## Issue

ESG "all-online-boutique-endpoints" PROVIDES contract "online-boutique-permit-to-all-endpoints-tcp-flags", the contract is CONSUMED by ESG "all-external-subnets"

The contract allows:
    - filter: tcp-c2p-src-any-dst-80-flag-syn
    - filter: tcp-c2p-src-any-dst-80-flag-est <-- includes ACK or RST
    - filter: tcp-c2p-src-any-dst-80-flag-fin
    - filter: tcp-p2c-src-80-dst-any-flag-ack

+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-----------+---------+-------+-------------+-------------+----------+
| FilterId |  Name | EtherT |    ArpOpc   | Prot | ApplyToFrag | Stateful |  SFromPort  |   SToPort   | DFromPort | DToPort |  Prio |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-----------+---------+-------+-------------+-------------+----------+
|   416    | 416_0 |   ip   | unspecified | tcp  |      no     |    no    | unspecified | unspecified |    http   |   http  | flags | unspecified | unspecified |   syn    |
|   426    | 426_0 |   ip   | unspecified | tcp  |      no     |    no    | unspecified | unspecified |    http   |   http  | flags | unspecified | unspecified |   est    |
|   428    | 428_0 |   ip   | unspecified | tcp  |      no     |    no    | unspecified | unspecified |    http   |   http  | flags | unspecified | unspecified |   fin    |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-----------+---------+-------+-------------+-------------+----------+

+----------+-------+--------+-------------+------+-------------+----------+-----------+---------+-------------+-------------+-------+-------------+-------------+----------+
| FilterId |  Name | EtherT |    ArpOpc   | Prot | ApplyToFrag | Stateful | SFromPort | SToPort |  DFromPort  |   DToPort   |  Prio |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+-------+--------+-------------+------+-------------+----------+-----------+---------+-------------+-------------+-------+-------------+-------------+----------+
|   444    | 444_0 |   ip   | unspecified | tcp  |      no     |    no    |    http   |   http  | unspecified | unspecified | flags | unspecified | unspecified |   ack    |
+----------+-------+--------+-------------+------+-------------+----------+-----------+---------+-------------+-------------+-------+-------------+-------------+----------+


ESG "all-online-boutique-endpoints" CONSUMES contract "online-boutique-permit-from-all-endpoints", the contract is PROVIDED by ESG "all-external-subnets"

The contract allows:
    - filter: tcp-c2p-src-any-dst-any-stateful

+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+
| FilterId |  Name | EtherT |    ArpOpc   | Prot | ApplyToFrag | Stateful |  SFromPort  |   SToPort   |  DFromPort  |   DToPort   |  Prio |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+
|   117    | 117_0 |   ip   | unspecified | tcp  |      no     |   yes    | unspecified | unspecified | unspecified | unspecified | proto | unspecified | unspecified |          |
|   118    | 118_0 |   ip   | unspecified | tcp  |      no     |   yes    | unspecified | unspecified | unspecified | unspecified | flags | unspecified | unspecified |   ack    |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+

Issue:

What appears to be happening is that if a Service Graph is applied to contract "online-boutique-permit-from-all-endpoints" it creates an overlap with traffic using contract "online-boutique-permit-to-all-endpoints-tcp-flags"

Traffic coming establised from outside via (p) ESG "all-external-subnets" to (c) ESG "all-online-boutique-endpoints" gets (unexpectedly) redirected by the Service Graph applied to contract "online-boutique-permit-from-all-endpoints"

Session from outside client:
    - SYN to destination port 80 -> matches filter 416
    - SYN/ACK from source port 80 -> matches filter 444
    - ACK to destination port 80 -> matches filter 426 and 118


https://www.cisco.com/c/en/us/products/collateral/networking/cloud-networking/application-centric-infrastructure/contract-guide.html#TCPflag

This option is to specify the TCP flag values to match traffic in addition to EtherType, IP protocol, source port, and destination port. 

The available TCP flags are:
    - Synchronize: SYN
    - Established: ACK or RST <- matches filter 118
    - Acknowledgement: ACK
    - Reset: RST
    - Finish: FIN

The confusion is possibly down to my interpretation of "TCP flag values to match traffic IN ADDITION to EtherType". My understanding is/was that traffic should have only matched filter 426 as it has a destination port of 80 AND a TCP flag of EST, however it is matching filter 118 (I can see this on the firewall) - there's not a "longest match" logic, therefore it's matching and redirecting. 




online-boutique-permit-from-all-endpoints-tcp-flags-syn-est-fin
online-boutique-permit-from-all-endpoints-tcp-flags-ack





        - name: 'tcp-c2p-src-any-dst-8099-flag-syn-stateful'
          entries:
            - name: 'tcp-c2p-src-any-dst-8099-flag-syn-stateful'
              protocol: tcp
              source_from_port: unspecified
              source_to_port: unspecified
              destination_from_port: 8099
              destination_to_port: 8099
              stateful: yes
              tcp_rules: syn

        - name: 'tcp-c2p-src-any-dst-8099-flag-est-stateful'
          entries:
            - name: 'tcp-c2p-src-any-dst-8099-flag-est-stateful'
              protocol: tcp
              source_from_port: unspecified
              source_to_port: unspecified
              destination_from_port: 8099
              destination_to_port: 8099
              stateful: yes
              tcp_rules: est

        - name: 'tcp-c2p-src-any-dst-8099-flag-fin-stateful'
          entries:
            - name: 'tcp-c2p-src-any-dst-8099-flag-fin-stateful'
              protocol: tcp
              source_from_port: unspecified
              source_to_port: unspecified
              destination_from_port: 8099
              destination_to_port: 8099
              stateful: yes
              tcp_rules: fin


####################

show zoning-rule contract tech-elevate:online-boutique-permit-to-all-endpoints-tcp-flags

+---------+--------+--------+----------+----------------+---------+---------+----------------------------------------------------------------+------------------+----------------+
| Rule ID | SrcEPG | DstEPG | FilterID |      Dir       |  operSt |  Scope  |                              Name                              |      Action      |    Priority    |
+---------+--------+--------+----------+----------------+---------+---------+----------------------------------------------------------------+------------------+----------------+
|   4143  |  5484  | 10938  |   475    |    uni-dir     | enabled | 2293763 | tech-elevate:online-boutique-permit-to-all-endpoints-tcp-flags |      permit      | fully_qual(7)  |
|   4505  | 10938  |   49   |   514    |    uni-dir     | enabled | 2392069 | tech-elevate:online-boutique-permit-to-all-endpoints-tcp-flags | redir(destgrp-2) | fully_qual(7)  |
|   5557  |   49   | 10938  |   475    |    uni-dir     | enabled | 2392069 | tech-elevate:online-boutique-permit-to-all-endpoints-tcp-flags | redir(destgrp-2) | fully_qual(7)  |
|   4483  |  5484  | 10938  |   475    |    uni-dir     | enabled | 2392069 | tech-elevate:online-boutique-permit-to-all-endpoints-tcp-flags |      permit      | fully_qual(7)  |
|   4907  | 10938  |   49   |   516    |    uni-dir     | enabled | 2392069 | tech-elevate:online-boutique-permit-to-all-endpoints-tcp-flags | redir(destgrp-2) | fully_qual(7)  |
|   5525  |  5484  |   49   | default  |     bi-dir     | enabled | 2293763 | tech-elevate:online-boutique-permit-to-all-endpoints-tcp-flags |      permit      | src_dst_any(9) |
|   5559  |   49   |  5484  | default  | uni-dir-ignore | enabled | 2293763 | tech-elevate:online-boutique-permit-to-all-endpoints-tcp-flags |      permit      | src_dst_any(9) |
|   4238  | 10938  |   49   |   514    |    uni-dir     | enabled | 2293763 | tech-elevate:online-boutique-permit-to-all-endpoints-tcp-flags | redir(destgrp-2) | fully_qual(7)  |
|   4557  | 10938  |   49   |   516    |    uni-dir     | enabled | 2293763 | tech-elevate:online-boutique-permit-to-all-endpoints-tcp-flags | redir(destgrp-2) | fully_qual(7)  |
|   4227  | 10938  |   49   |   520    |    uni-dir     | enabled | 2293763 | tech-elevate:online-boutique-permit-to-all-endpoints-tcp-flags | redir(destgrp-2) | fully_qual(7)  |
|   5433  |   49   | 10938  |   475    |    uni-dir     | enabled | 2293763 | tech-elevate:online-boutique-permit-to-all-endpoints-tcp-flags | redir(destgrp-2) | fully_qual(7)  |
|   5545  | 10938  |   49   |   520    |    uni-dir     | enabled | 2392069 | tech-elevate:online-boutique-permit-to-all-endpoints-tcp-flags | redir(destgrp-2) | fully_qual(7)  |
+---------+--------+--------+----------+----------------+---------+---------+----------------------------------------------------------------+------------------+----------------+

+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-----------+---------+-------+-------------+-------------+----------+
| FilterId |  Name | EtherT |    ArpOpc   | Prot | ApplyToFrag | Stateful |  SFromPort  |   SToPort   | DFromPort | DToPort |  Prio |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-----------+---------+-------+-------------+-------------+----------+
|   514    | 514_0 |   ip   | unspecified | tcp  |      no     |   yes    | unspecified | unspecified |    http   |   http  | flags | unspecified | unspecified |   syn    |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-----------+---------+-------+-------------+-------------+----------+

+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-----------+---------+-------+-------------+-------------+----------+
| FilterId |  Name | EtherT |    ArpOpc   | Prot | ApplyToFrag | Stateful |  SFromPort  |   SToPort   | DFromPort | DToPort |  Prio |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-----------+---------+-------+-------------+-------------+----------+
|   520    | 520_0 |   ip   | unspecified | tcp  |      no     |   yes    | unspecified | unspecified |    http   |   http  | flags | unspecified | unspecified |   est    |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-----------+---------+-------+-------------+-------------+----------+

+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-----------+---------+-------+-------------+-------------+----------+
| FilterId |  Name | EtherT |    ArpOpc   | Prot | ApplyToFrag | Stateful |  SFromPort  |   SToPort   | DFromPort | DToPort |  Prio |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-----------+---------+-------+-------------+-------------+----------+
|   516    | 516_0 |   ip   | unspecified | tcp  |      no     |   yes    | unspecified | unspecified |    http   |   http  | flags | unspecified | unspecified |   fin    |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-----------+---------+-------+-------------+-------------+----------+

+----------+-------+--------+-------------+------+-------------+----------+-----------+---------+-------------+-------------+-------+-------------+-------------+----------+
| FilterId |  Name | EtherT |    ArpOpc   | Prot | ApplyToFrag | Stateful | SFromPort | SToPort |  DFromPort  |   DToPort   |  Prio |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+-------+--------+-------------+------+-------------+----------+-----------+---------+-------------+-------------+-------+-------------+-------------+----------+
|   475    | 475_0 |   ip   | unspecified | tcp  |      no     |   yes    |    http   |   http  | unspecified | unspecified | flags | unspecified | unspecified |   ack    |
+----------+-------+--------+-------------+------+-------------+----------+-----------+---------+-------------+-------------+-------+-------------+-------------+----------+




show zoning-rule contract tech-elevate:online-boutique-permit-to-all-endpoints-tcp-flags
+---------+--------+--------+----------+---------+---------+---------+------------------------------------------------------------------+--------+---------------+
| Rule ID | SrcEPG | DstEPG | FilterID |   Dir   |  operSt |  Scope  |                               Name                               | Action |    Priority   |
+---------+--------+--------+----------+---------+---------+---------+------------------------------------------------------------------+--------+---------------+
|   5535  |   49   | 10938  |   117    | uni-dir | enabled | 2392069 | tech-elevate:online-boutique-permit-from-all-endpoints-tcp-flags | permit | fully_qual(7) |
|   5391  | 10938  |   49   |   118    | uni-dir | enabled | 2293763 | tech-elevate:online-boutique-permit-from-all-endpoints-tcp-flags | permit | fully_qual(7) |
|   5565  |   49   | 10938  |   117    | uni-dir | enabled | 2293763 | tech-elevate:online-boutique-permit-from-all-endpoints-tcp-flags | permit | fully_qual(7) |
|   4879  | 10938  |   49   |   118    | uni-dir | enabled | 2392069 | tech-elevate:online-boutique-permit-from-all-endpoints-tcp-flags | permit | fully_qual(7) |
+---------+--------+--------+----------+---------+---------+---------+------------------------------------------------------------------+--------+---------------+

+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+
| FilterId |  Name | EtherT |    ArpOpc   | Prot | ApplyToFrag | Stateful |  SFromPort  |   SToPort   |  DFromPort  |   DToPort   |  Prio |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+
|   117    | 117_0 |   ip   | unspecified | tcp  |      no     |   yes    | unspecified | unspecified | unspecified | unspecified | proto | unspecified | unspecified |          |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+

+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+
| FilterId |  Name | EtherT |    ArpOpc   | Prot | ApplyToFrag | Stateful |  SFromPort  |   SToPort   |  DFromPort  |   DToPort   |  Prio |   Icmpv4T   |   Icmpv6T   | TcpRules |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+
|   118    | 118_0 |   ip   | unspecified | tcp  |      no     |   yes    | unspecified | unspecified | unspecified | unspecified | flags | unspecified | unspecified |   ack    |
+----------+-------+--------+-------------+------+-------------+----------+-------------+-------------+-------------+-------------+-------+-------------+-------------+----------+



This does the ack from the outside to the servers doesn't get through to the firewall unless the SG is applied to the "from" contract


#############



# Cisco ACI Contract and Filter Priorities

Source: Cisco ACI Contract Guide White Paper  
https://www.cisco.com/c/en/us/products/collateral/networking/cloud-networking/application-centric-infrastructure/contract-guide.html

**Priority rule:** lower number = higher priority.

## Contract / zoning-rule priorities

+----------+--------------------------------+-----------------------+------------------------+----------------------------------------------------------------------------------+
| Priority | Zoning rule                    | Source → Destination  | Filter                 | Notes                                                                            |
| -------: | ------------------------------ | --------------------- | ---------------------- | -------------------------------------------------------------------------------- |
|    **1** | Intra-EPG contract             | EPG → same EPG        | Specific               | Permit, deny, redirect, copy                                                     |
|    **2** | Intra-EPG isolation            | EPG → same EPG        | Implicit / unspecified | Deny, log                                                                        |
|    **3** | Intra-EPG permit               | EPG → same EPG        | Implicit / unspecified | System startup rule                                                              |
|    **4** | Reserved                       | —                     | —                      | Reserved by system                                                               |
|    **5** | Taboo contract                 | Any → specific EPG    | Specific/default       | Denies traffic destined to the EPG                                               |
|    **6** | Reserved                       | —                     | —                      | Reserved by system                                                               |
|    **7** | EPG → EPG                      | Specific → specific   | Specific               | `fully_qual(7)`                                                                  |
|    **8** | System error                   | —                     | —                      | Rule programming incomplete/error                                                |
|    **9** | EPG → EPG                      | Specific → specific   | Default / any          | `src_dst_any(9)`                                                                 |
|   **10** | EPG → vzAny / ESG → vzAny      | Specific → any        | Specific               | ESG → vzAny uses priority 10 because ESG uses the global class-ID range          |
|   **11** | Reserved / system              | —                     | —                      | Non-user-defined priority; may change                                            |
|   **12** | Inter-VRF source-specific deny | Specific source → any | Any                    | System-generated inter-VRF deny                                                  |
|   **13** | EPG → vzAny                    | Specific → any        | Specific               | `shsrc_any_filt_perm(13)`                                                        |
|   **14** | vzAny → EPG                    | Any → specific        | Specific               | Specific filter                                                                  |
|   **15** | EPG → vzAny                    | Specific → any        | Default / any          | Default filter                                                                   |
|   **16** | vzAny → EPG                    | Any → specific        | Default / any          | `any_dest_any(16)`                                                               |
|   **17** | vzAny → vzAny                  | Any → any             | Specific               | `any_any_filter(17)`                                                             |
|   **18** | Preferred-group implicit deny  | Specific → any        | Any                    | System-generated                                                                 |
|   **19** | Preferred-group implicit deny  | Any → specific        | Any                    | System-generated; priority may change depending on preferred-group configuration |
|   **20** | Preferred-group permit         | Any → any             | Any                    | `grp_any_any_any_permit(20)`                                                     |
|   **21** | Implicit deny                  | Any → any             | Any                    | `any_any_any(21)`                                                                |
|   **22** | L3Out / VRF implicit deny      | Any → L3Out           | Any                    | `any_vrf_any_deny(22)`; priority can change when preferred group is enabled      |
+----------+--------------------------------+-----------------------+------------------------+----------------------------------------------------------------------------------+

## Filter priorities

Filter priority is considered when applicable zoning rules have the same zoning-rule priority. Specific protocols and L4 ports win; a specific destination port is more specific than a specific source port.

+-----------------+------------------------------------------------+----------------+------------------+
| Filter priority | Match criteria                                 | Source port    | Destination port |
| --------------: | ---------------------------------------------- | -------------- | ---------------- |
|           **1** | TCP flag selected                              | Any / specific | Any / specific   |
|           **2** | Specific protocol                              | Specific       | Specific         |
|           **3** | Specific protocol                              | Any            | Specific         |
|           **4** | Specific protocol                              | Specific       | Any              |
|           **5** | Specific protocol                              | Any            | Any              |
|           **6** | Match Only Fragments enabled                   | Any / specific | Any / specific   |
|           **7** | EtherType unspecified / default filter         | —              | —                |
|           **8** | EtherType unspecified / implicit system filter | —              | —                |
+-----------------+------------------------------------------------+----------------+------------------+

## Key points

- Lower numeric priority means higher priority.
- Zoning-rule priority is considered before filter specificity.
- EPG-to-EPG is more specific than EPG-to-vzAny, which is more specific than vzAny-to-vzAny.
- A specific filter is more specific than the default/any filter.
- Within the same zoning-rule priority, deny wins over permit or redirect.
- For permit versus redirect at the same zoning-rule priority, the more-specific protocol/L4 filter wins.
- TCP-flag filters have filter priority **1**.
- A normal EPG-to-EPG contract using a specific filter therefore has zoning-rule priority **7**, with the TCP-flag filter itself having filter priority **1**.