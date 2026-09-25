#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
pySROS Script: Check Binding-SIDs in YANG State Datastore on Nokia SR OS.
Target: R2 in lab-gilles (or any SR OS node).

Lists all Binding-SIDs found in the state datastore with:
- Associated entity (SR-TE LSP or SR-Policy)
- Operational status (Up / Down)
- Endpoint IP address
- Number of hops (segments / actual route hops)
"""

import sys

try:
    from pysros.management import connect
    from pysros.pprint import Table
    from pysros.exceptions import SrosMgmtError
except ImportError:
    print("Error: pySROS library is not available in the current environment.")
    sys.exit(1)


def decode_endpoint_from_lsp_id(lsp_id_val):
    """
    Decodes the 32-bit destination IPv4 address from the hex lsp-id string:
    lsp-id format: 0x<from:4B><path-lsp-id:2B><to:4B><tunnel-id:2B>...
    e.g.: 0xc00002023002c000020800050000000000000000
    c0.00.02.08 -> 192.0.2.8
    """
    try:
        s = str(lsp_id_val)
        if s.startswith("0x") and len(s) >= 22:
            hex_to = s[14:22]
            octets = [str(int(hex_to[i:i+2], 16)) for i in range(0, 8, 2)]
            return ".".join(octets)
    except Exception:
        pass
    return "N/A"


def get_connection(host=None, username=None, password=None, port=830):
    """
    Establishes connection to SR OS.
    If run on-box via pyexec, connect() without arguments attaches locally.
    If run off-box, uses provided or default management credentials.
    """
    if host:
        return connect(
            host=host,
            username=username or "admin",
            password=password or "NokiaSros1!",
            port=port,
            hostkey_verify=False
        )
    try:
        # On-box attempt
        return connect()
    except Exception:
        # Off-box fallback for lab-gilles R2
        return connect(
            host="172.100.30.2",
            username=username or "admin",
            password=password or "NokiaSros1!",
            port=port,
            hostkey_verify=False
        )


def check_binding_sids(conn, router_name="Base"):
    """
    Inspects YANG state datastore for all Binding-SIDs related to
    SR-TE LSPs and SR-Policies.
    """
    results = []

    # -------------------------------------------------------------
    # 1. Fetch MPLS actual-route-hop-list & LSPs from State
    # -------------------------------------------------------------
    ar_hop_list = {}
    try:
        ar_hops_data = conn.running.get(
            '/nokia-state:state/router[router-name="{0}"]/mpls/actual-route-hop-list'.format(router_name)
        )
        if ar_hops_data:
            ar_hop_list = ar_hops_data
    except Exception:
        pass

    try:
        mpls_lsps = conn.running.get(
            '/nokia-state:state/router[router-name="{0}"]/mpls/lsp'.format(router_name)
        )
    except Exception:
        mpls_lsps = {}

    if mpls_lsps:
        for lsp_name, lsp_data in mpls_lsps.items():
            bsid_leaf = lsp_data.get('lsp-binding-sid')
            if not bsid_leaf:
                continue

            bsid_val = bsid_leaf.data if hasattr(bsid_leaf, 'data') else bsid_leaf
            if not bsid_val or bsid_val == 0:
                continue

            # Operational state
            oper_leaf = lsp_data.get('oper-state')
            oper_str = oper_leaf.data if hasattr(oper_leaf, 'data') else str(oper_leaf)
            is_oper = (str(oper_str).lower() == "up")
            oper_display = "Up" if is_oper else "Down"

            # Endpoint address
            endpoint = "N/A"
            try:
                to_leaf = conn.running.get(
                    '/nokia-conf:configure/router[router-name="{0}"]/mpls/lsp[lsp-name="{1}"]/to'.format(
                        router_name, lsp_name
                    )
                )
                if to_leaf:
                    endpoint = to_leaf.data if hasattr(to_leaf, 'data') else str(to_leaf)
            except Exception:
                pass

            # Hop count from primary path actual-route-hop-list
            hops = 0
            ar_idx = 0
            primary_dict = lsp_data.get('primary', {})
            if primary_dict:
                for prim_name, prim_data in primary_dict.items():
                    # Fallback to decode endpoint from lsp-id if configure get failed
                    if endpoint == "N/A" and 'lsp-id' in prim_data:
                        lsp_id_val = prim_data['lsp-id'].data if hasattr(prim_data['lsp-id'], 'data') else str(prim_data['lsp-id'])
                        endpoint = decode_endpoint_from_lsp_id(lsp_id_val)

                    # Prefer active path if available
                    path_state = prim_data.get('path-state')
                    path_state_str = path_state.data if hasattr(path_state, 'data') else str(path_state)
                    if path_state_str == "active" or ar_idx == 0:
                        ar_idx_leaf = prim_data.get('ar-hop-list-index')
                        if ar_idx_leaf:
                            ar_idx = ar_idx_leaf.data if hasattr(ar_idx_leaf, 'data') else ar_idx_leaf

            if ar_idx and ar_idx > 0 and ar_hop_list:
                hops = sum(1 for k in ar_hop_list.keys() if isinstance(k, tuple) and k[0] == ar_idx)

            # Determine if LSP is PCC(-init) or PCE(-init)
            lsp_init = "PCC-init"
            origin_template = lsp_data.get('origin-template')
            orig_tmpl_str = origin_template.data if hasattr(origin_template, 'data') else str(origin_template or "")
            if orig_tmpl_str:
                lsp_init = "PCE-init"
            else:
                try:
                    type_leaf = conn.running.get(
                        '/nokia-conf:configure/router[router-name="{0}"]/mpls/lsp[lsp-name="{1}"]/type'.format(
                            router_name, lsp_name
                        )
                    )
                    type_str = str(type_leaf.data if hasattr(type_leaf, 'data') else type_leaf).lower()
                    if "pce-init" in type_str:
                        lsp_init = "PCE-init"
                    elif "sr-te" in type_str:
                        lsp_init = "PCC-init"
                except Exception:
                    pass

            results.append({
                "binding_sid": int(bsid_val),
                "type": "SR-TE LSP ({0})".format(lsp_init),
                "name": str(lsp_name),
                "endpoint": str(endpoint),
                "operational": oper_display,
                "is_oper": is_oper,
                "hops": hops
            })

    # -------------------------------------------------------------
    # 2. Fetch SR-Policies from State Datastore
    # -------------------------------------------------------------
    # Check static-policy config to get user-defined policy names
    static_policy_names = {}
    try:
        sp_conf = conn.running.get(
            '/nokia-conf:configure/router[router-name="{0}"]/segment-routing/sr-policies/static-policy'.format(router_name)
        )
        if sp_conf:
            for pol_name, pol_data in sp_conf.items():
                c_leaf = pol_data.get('color')
                ep_leaf = pol_data.get('endpoint')
                color_val = c_leaf.data if hasattr(c_leaf, 'data') else c_leaf
                ep_val = ep_leaf.data if hasattr(ep_leaf, 'data') else ep_leaf
                if color_val is not None and ep_val is not None:
                    static_policy_names[(int(color_val), str(ep_val))] = str(pol_name)
    except Exception:
        pass

    try:
        sr_policies = conn.running.get(
            '/nokia-state:state/router[router-name="{0}"]/segment-routing/sr-policies'.format(router_name)
        )
    except Exception:
        sr_policies = {}

    if sr_policies and 'sr-path' in sr_policies:
        for path_key, path_data in sr_policies['sr-path'].items():
            bsid_leaf = path_data.get('binding-sid')
            if not bsid_leaf:
                continue

            bsid_val = bsid_leaf.data if hasattr(bsid_leaf, 'data') else bsid_leaf
            if not bsid_val or bsid_val == 0:
                continue

            # Operational state
            oper_leaf = path_data.get('is-candidate-path-operational')
            oper_val = oper_leaf.data if hasattr(oper_leaf, 'data') else bool(oper_leaf)
            is_oper = bool(oper_val)
            oper_display = "Up" if is_oper else "Down"

            # Endpoint and color
            ep_leaf = path_data.get('endpoint')
            endpoint = str(ep_leaf.data if hasattr(ep_leaf, 'data') else ep_leaf)

            c_leaf = path_data.get('color')
            color = int(c_leaf.data if hasattr(c_leaf, 'data') else c_leaf)

            owner_leaf = path_data.get('owner')
            owner_val = str(owner_leaf.data if hasattr(owner_leaf, 'data') else owner_leaf).lower()

            # Name / Identifier with color always between brackets
            type_str = "SR-Policy ({0})".format(owner_val.upper())
            if (color, endpoint) in static_policy_names:
                name_str = "{0} [Color {1}]".format(static_policy_names[(color, endpoint)], color)
            else:
                name_str = "Policy [Color {0}]".format(color)

            # Number of hops from segment list
            hops = 0
            seg_list_dict = path_data.get('sr-path-seg-list', {})
            if seg_list_dict:
                for seg_idx, seg_data in seg_list_dict.items():
                    if 'segments' in seg_data:
                        seg_leaf = seg_data['segments']
                        hops = seg_leaf.data if hasattr(seg_leaf, 'data') else int(seg_leaf)
                        break
                    elif 'segment' in seg_data:
                        hops = len(seg_data['segment'])
                        break

            results.append({
                "binding_sid": int(bsid_val),
                "type": type_str,
                "name": name_str,
                "endpoint": endpoint,
                "operational": oper_display,
                "is_oper": is_oper,
                "hops": hops
            })

    # Sort results by Binding-SID
    results.sort(key=lambda x: x["binding_sid"])
    return results


def print_results_table(results, router_name="Base"):
    """
    Renders the Binding-SID information using pySROS Table.
    """
    cols = [
        (13, "Binding-SID"),
        (23, "Type"),
        (38, "Name / Identifier"),
        (16, "Endpoint"),
        (13, "Operational"),
        (6, "Hops"),
    ]

    title = "YANG State Binding-SID Inventory (Router: {0})".format(router_name)
    table = Table(title, cols, width=113)

    rows = []
    up_count = 0
    down_count = 0

    for item in results:
        rows.append((
            str(item["binding_sid"]),
            item["type"],
            item["name"],
            item["endpoint"],
            item["operational"],
            str(item["hops"])
        ))
        if item["is_oper"]:
            up_count += 1
        else:
            down_count += 1

    table.print(rows)
    print("Summary: Total Binding-SIDs: {0} | Operational (Up): {1} | Non-Operational (Down): {2}".format(
        len(results), up_count, down_count
    ))
    print("")


def main():
    router = "Base"
    host = None
    username = "admin"
    password = "NokiaSros1!"
    port = 830

    # Lightweight manual argument parsing for embedded Python
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--host" and i + 1 < len(args):
            host = args[i+1]
            i += 2
        elif arg == "--username" and i + 1 < len(args):
            username = args[i+1]
            i += 2
        elif arg == "--password" and i + 1 < len(args):
            password = args[i+1]
            i += 2
        elif arg == "--port" and i + 1 < len(args):
            port = int(args[i+1])
            i += 2
        elif arg == "--router" and i + 1 < len(args):
            router = args[i+1]
            i += 2
        else:
            i += 1

    conn = get_connection(
        host=host,
        username=username,
        password=password,
        port=port
    )

    results = check_binding_sids(conn, router_name=router)
    print_results_table(results, router_name=router)


if __name__ == "__main__":
    main()
