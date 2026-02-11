# ACI Endpoint Discovery & ESG Automation with Terraform

This Terraform project automates the discovery of endpoints in Cisco ACI and dynamically builds
Application Profiles, Endpoint Security Groups (ESGs), MAC-based tags, and VRF associations based on
live APIC data and a simple CSV input file.

The workflow is fully data‑driven: you provide a CSV containing application names, tenants, and IP
addresses, and Terraform automatically discovers MAC addresses, Bridge Domains, VRFs, and constructs
the appropriate ACI objects.

---

## 🚀 Features

### 🔍 Dynamic Endpoint Discovery

For each IP address in the CSV:

- Queries APIC for the corresponding `fvIp` object  
- Extracts the MAC address  
- Queries `fvCEp` to determine the Bridge Domain and VRF  
- Parses the VRF name from the `vrfDn` (e.g., `ctx-vrf-01` → `vrf-01`)

### 🏷 Automatic MAC Tagging

Each discovered MAC address is tagged with:

- A user‑defined tag key (default: `ApplicationName`)
- The application name from the CSV

### 🏗 Automatic Application Profile Creation

One Application Profile is created per unique application.

### 🔐 ESG Creation & Configuration

For each application:

- Creates an ESG inside the Application Profile  
- Applies isolation mode (`enforced` / `unenforced`)  
- Applies preferred‑group membership (`include` / `exclude`)  
- Associates the ESG with the discovered VRF  

### 🏷 ESG Tag Selectors

Each ESG automatically selects endpoints based on the MAC tags created earlier.

### 📄 CSV‑Driven Input

The CSV file defines:

- tenant
- application_name
- ip_address
- isolated status
- preferred-group status
