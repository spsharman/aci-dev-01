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