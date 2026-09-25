# Custom MD-CLI Command: `show router mpls list-binding-sid`

**Author / Maintainer**: Network Engineering Automation  
**Target Platform**: Nokia SR OS (7750 SR, 7950 XRS, 7250 IXR)  
**Supported Releases**: SR OS 21.x – 26.x (Validated and tested on **SR OS Release 26.3.R1** / TiMOS-26.3.R1)  
**Engine**: On-box pySROS / MicroPython 3.4 & Model-Driven CLI (MD-CLI)  

---

## 1. Executive Summary & Operational Problem

In Segment Routing (SR-MPLS) networks, **Binding-SIDs (BSIDs)** are central to traffic engineering, service stitching, inter-domain path mapping, and controller-directed path selection. A Binding-SID binds an incoming MPLS label to a specific Traffic-Engineered path—either a **Segment Routing Traffic Engineering (SR-TE) LSP** or an **SR Policy** (configured statically or signaled via BGP-SR-Policy / PCEP).

### The Operational Challenge in Native CLI
Out-of-the-box in Nokia SR OS, there is no single command that provides a consolidated, network-wide inventory of all active Binding-SIDs on a router. Network engineers troubleshooting traffic steering or verifying controller path allocations currently have to navigate separate, disjoint CLI hierarchies:
- `show router mpls sr-te-lsp <lsp-name> path detail` for SR-TE LSPs
- `show router segment-routing sr-policies sr-path` for SR Policies
- Inspect individual candidate paths, segment lists, and operational states across multiple paginated outputs.

### The Solution: `show router mpls list-binding-sid`
Using Nokia's on-box **pySROS** automation framework, this custom tool extracts and correlates data from the native Nokia YANG state datastores into a single, clean, tabular show command: **`show router mpls list-binding-sid`**.

It delivers:
1. Complete list of all allocated Binding-SIDs (sorted numerically).
2. Protocol & Origin: Clearly distinguishes `SR-TE LSP (PCC-init)`, `SR-TE LSP (PCE-init)`, `SR-Policy (STATIC)`, and `SR-Policy (BGP)`.
3. Identity & Color: Displays user-defined names with color formatted as `[Color <id>]`.
4. Endpoint: Egress router IPv4 system address.
5. Calculated Hop Count: Actual number of hops traversed along the active path.
6. Operational State: Real-time health status (`Up` or `Down`).
7. Inventory Totals: A summary tally of total BSIDs and their operational status.

---

## 2. Command Outcome & Output Description

### Live Command Execution Example

Below is the live output captured directly from **R2** (7750 SR-1s running SR OS 26.3.R1):

```text
[/]
A:admin@R2# show router mpls list-binding-sid
=================================================================================================================
YANG State Binding-SID Inventory (Router: Base)
=================================================================================================================
Binding-SID   Type                    Name / Identifier                      Endpoint         Operational   Hops  
-----------------------------------------------------------------------------------------------------------------
24241         SR-Policy (STATIC)      BSID-R2-R4-via-R22 [Color 102]         192.0.2.4        Down          4     
24242         SR-Policy (STATIC)      SR-POL-R1-R6-via-BSID [Color 100]      192.0.2.6        Down          3     
500013        SR-Policy (BGP)         Policy [Color 10013]                   192.168.8.8      Up            3     
500014        SR-Policy (BGP)         Policy [Color 10014]                   192.168.8.8      Up            3     
500028        SR-Policy (STATIC)      BSID-R2-R8-via-R4 [Color 2345]         192.0.2.8        Up            3     
500050        SR-Policy (BGP)         Policy [Color 888]                     192.0.2.8        Up            3     
500408        SR-TE LSP (PCC-init)    SRTE-BSID-R2-R8                        192.0.2.8        Up            3     
=================================================================================================================
Summary: Total Binding-SIDs: 7 | Operational (Up): 5 | Non-Operational (Down): 2
```

Below is another example captured from **R1** (7750 SR-1 running SR OS 26.3.R1):

```text
[/]
A:admin@R1# show router mpls list-binding-sid
=================================================================================================================
YANG State Binding-SID Inventory (Router: Base)
=================================================================================================================
Binding-SID   Type                    Name / Identifier                      Endpoint         Operational   Hops  
-----------------------------------------------------------------------------------------------------------------
24005         SR-Policy (STATIC)      test-policy-wouter [Color 101]         192.0.2.6        Up            1     
24242         SR-Policy (BGP)         Policy [Color 100]                     192.0.2.6        Up            3     
=================================================================================================================
Summary: Total Binding-SIDs: 2 | Operational (Up): 2 | Non-Operational (Down): 0
```

---

### Output Fields Specification

| Column Header | Field Type | Description |
| :--- | :--- | :--- |
| **`Binding-SID`** | Integer / Label | The 20-bit or 32-bit MPLS label value assigned as the Binding Segment Routing Identifier. Sourced from the router's reserved BSID label block or static reservation pool. |
| **`Type`** | String Enum | Identifies the traffic engineering tunneling technology and originator:<br>• `SR-TE LSP (PCC-init)`: Router-initiated SR-TE LSP computed via local CSPF.<br>• `SR-TE LSP (PCE-init)`: Controller-initiated SR-TE LSP via PCEP (e.g. Nokia NSP).<br>• `SR-Policy (STATIC)`: Segment routing policy manually defined under `/configure router segment-routing sr-policies static-policy`.<br>• `SR-Policy (BGP)`: Dynamically signaled SR Policy received via BGP IPv4/IPv6 SR-Policy address family (AFI 1/2, SAFI 73). |
| **`Name / Identifier`** | String | The human-readable name of the LSP or Policy. For all SR Policies, the TE color community is encapsulated inside brackets `[Color <id>]` for fast visual correlation with BGP route colors. |
| **`Endpoint`** | IPv4 Address | The destination IP address (system loopback) of the tail-end node where the tunnel terminates. |
| **`Operational`** | State (`Up` / `Down`) | Real-time forwarding plane health of the tunnel. For SR Policies, indicates whether the active candidate path is operational and valid. |
| **`Hops`** | Integer | The exact count of hops traversed along the active path. Sourced dynamically from the actual route hop list (`actual-route-hop-list`) for LSPs, or the active segment list (`sr-path-seg-list`) for SR Policies. |
| **`Summary`** | Tally Bar | Aggregates the total count of Binding-SIDs and breaks down the number of operational (`Up`) versus faulted (`Down`) paths. |

---

## 3. Architecture & YANG Datastore Modeling

The script interacts directly with the SR OS YANG state datastore via the embedded `pysros.management.connect()` API. No external network connections, sockets, or off-box orchestrators are required.

```
                      +---------------------------------------+
                      |       MD-CLI Operator Session         |
                      |  # show router mpls list-binding-sid  |
                      +---------------------------------------+
                                          |
                                          v  (command-alias)
                      +---------------------------------------+
                      |         pyexec list-binding-sid       |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |   check_binding_sids.py (pySROS)      |
                      +---------------------------------------+
                                    |           |
            +-----------------------+           +-----------------------+
            v                                                           v
  +--------------------+                                      +--------------------+
  |    nokia-state     |                                      |    nokia-conf      |
  |  State Datastore   |                                      |  Config Datastore  |
  +--------------------+                                      +--------------------+
  | • mpls/lsp         |                                      | • mpls/lsp/to      |
  | • actual-route-hops|                                      | • sr-policies/     |
  | • sr-policies/     |                                      |   static-policy    |
  |   sr-path          |                                      +--------------------+
  +--------------------+
```

### YANG Paths Queried

1. **SR-TE LSP State**:
   - Path: `/nokia-state:state/router[router-name="Base"]/mpls/lsp`
   - Retrieved Leaves: `lsp-name`, `lsp-binding-sid`, `oper-state`, `primary`, `origin-template`.
2. **MPLS Actual Route Hops**:
   - Path: `/nokia-state:state/router[router-name="Base"]/mpls/actual-route-hop-list`
   - Correlates the `ar-hop-list-index` of the active primary path to count physical transit hops.
3. **Tail-End Address Resolution**:
   - Path: `/nokia-conf:configure/router[router-name="Base"]/mpls/lsp[lsp-name="..."]/to`
   - Fallback: Bitwise hexadecimal extraction from 32-bit `lsp-id` (`0x<src:4B><path:2B><dst:4B><tunnel:2B>`).
4. **SR-Policy State**:
   - Path: `/nokia-state:state/router[router-name="Base"]/segment-routing/sr-policies/sr-path`
   - Retrieved Leaves: `binding-sid`, `endpoint`, `color`, `owner`, `is-candidate-path-operational`, `sr-path-seg-list`.
5. **Static SR-Policy Configurations**:
   - Path: `/nokia-conf:configure/router[router-name="Base"]/segment-routing/sr-policies/static-policy`
   - Maps user-defined policy administrative names to `(color, endpoint)` pairs.

---

## 4. Installation & Deployment Guide

Deployment requires three steps:
1. Placing the script on the router's storage.
2. Registering the python script in the configuration.
3. Declaring the MD-CLI command alias.

### Step 1: Copy Script to Storage

#### Option A: Local Flash Storage (`cf3:\`)
On physical routers (7750 SR / 7250 IXR) and Containerlab `nokia_srsim` nodes, copy `check_binding_sids.py` to `cf3:\`:
```bash
# Via SCP / SFTP to router:
scp check_binding_sids.py admin@<router-ip>:cf3:/check_binding_sids.py
```

#### Option B: Remote URL (HTTP / TFTP)
SR OS can load python scripts directly from internal network repositories or TFTP servers (standard on `vr-sros` Containerlab nodes):
```text
urls ["tftp://172.31.255.29/check_binding_sids.py"]
# or
urls ["http://192.168.100.1/scripts/check_binding_sids.py"]
```

---

### Step 2: Register the Python Script in MD-CLI

Enter MD-CLI configuration mode and declare the python script:

```sros
/configure private
python {
    python-script "list-binding-sid" {
        admin-state enable
        urls ["cf3:\check_binding_sids.py"]
        version python3
    }
}
/commit
```

> [!NOTE]
> On virtual `vr-sros` environments where flash is network-booted, replace `"cf3:\check_binding_sids.py"` with your TFTP or HTTP URL (e.g., `"tftp://172.31.255.29/check_binding_sids.py"`).

---

### Step 3: Create the MD-CLI Command Alias

Configure the custom alias to bind `show router mpls list-binding-sid` to the python execution engine:

```sros
/configure private
system {
    management-interface {
        cli {
            md-cli {
                environment {
                    command-alias {
                        alias "show router mpls list-binding-sid" {
                            admin-state enable
                            description "Display all Binding-SIDs for SR-TE LSPs and SR Policies"
                            expansion "pyexec list-binding-sid"
                        }
                    }
                }
            }
        }
    }
}
/commit
/exit all
admin save
```

> [!IMPORTANT]
> **Session Invariant**:
> New MD-CLI command aliases take effect on **newly created CLI sessions**. If you test the command in the same SSH connection where you defined the alias, exit and start a fresh session, or invoke `pyexec list-binding-sid` directly.

---

## 5. Compatibility & Engineering Guardrails

### 1. SR OS Release Support
- **SR OS 26.x (Tested on 26.3.R1)**: Native compatibility.
- **SR OS 22.x – 25.x**: Supported out of the box with `pysros` module.
- **SR OS 21.x**: Supported on builds with on-box Python 3 enabled.

### 2. On-Box Python 3.4 Runtime Invariant
The embedded CPM execution environment runs **MicroPython / Python 3.4.0**:
- **No Python 3.5+ Syntax**: Do **not** use f-strings (`f"..."`) or `async`/`await`. All formatting uses `.format()` or `%`.
- **Zero External Modules**: The environment does not bundle `argparse`, `socket`, `requests`, or third-party packages. The script is strictly self-contained, using `pysros.management`, `pysros.pprint.Table`, and `sys`.
- **IP Address Unpacking**: Decoding IP addresses from binary/hex identifiers is implemented with pure string slicing (`int(hex, 16)`), avoiding dependence on missing C-extension libraries.

### 3. Model-Driven Mode Prerequisite
Command aliases require the node management interface to operate in pure model-driven mode:
```sros
system {
    management-interface {
        configuration-mode model-driven
    }
}
```
*If a router is configured in `configuration-mode mixed`, attempting to commit a `command-alias` triggers `MINOR: MGMT_CORE #4001: Command alias is only supported in model-driven configuration mode`.*

### 4. Hardware Platform Scope
- **Fully Supported**: 7750 SR (all variants: SR-1, SR-1s, SR-7, SR-12, SR-14s, SR-1x), 7950 XRS, 7250 IXR (IXR-s, IXR-e, IXR-R6, IXR-x).
- **Not Supported**: 7705 SAR platforms (SAR OS / SAR-1) do not embed the on-box pySROS Python execution engine.

---

## 6. Verification and Troubleshooting Checklist

| Symptom | Cause | Remediation |
| :--- | :--- | :--- |
| `MINOR: CLI #2001: Unknown element - 'list-binding-sid'` | Alias was committed in current session but session cache has not refreshed. | Log out and start a fresh MD-CLI session (`exit` and re-SSH), or run `pyexec list-binding-sid`. |
| `MINOR: MGMT_CORE #4001: Command alias is only supported...` | Router is running in `mixed` configuration mode. | Switch to model-driven mode: `/configure system management-interface configuration-mode model-driven`, commit, and re-apply alias. |
| `Error: pySROS library is not available` | Executed under standard Linux python without the `pysros` wheel installed. | Run on-box via `pyexec list-binding-sid` or install `pip install pysros` on your off-box automation host. |
| `Empty table / 0 Binding-SIDs` | No SR-TE LSPs or SR Policies have an allocated Binding-SID in the `Base` router. | Verify underlay Segment Routing configuration and confirm that `binding-sid` is configured under `mpls lsp` or `sr-policies`. |

---

