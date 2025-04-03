#!/usr/bin/env python3
 
import sys, json
from pysros.management import connect
from pysros.pprint import Table

credentials = {
    "port": 830,
}

def PrintSvcTable(PrintResult):
    # 
    # Printresult is a dictionary with LSP as key, and a list of svc tuples as values
    # 
    # build the columns
    cols = [
        (30, "Service name"),
        (17, "Service type"),
        (10, "Service ID")
    ]

    # print the output on a per-LSP basis
    for lspPrint, service in PrintResult.items():
        # build the title with the lsp-name, lsp-type and tunnel-id
        lspNamePrint, lspTypePrint, lspTtmPrint = lspPrint
        title = ("lsp %s of type %s with tunnel-id %s used in:" % (lspNamePrint, lspTypePrint, lspTtmPrint))
    
        # Initalize the Table object with the heading and columns.
        table = Table(title, cols)

        # Print the output passing the data for each service in the value, linked to the key (lsp)
        table.print(service)


def main():
# start: get LSP name if present
    input_lsp = 0
    input_lsp = input("which LSP you want to check ? (lsp-name or ENTER for all)  : ")
    # check number of params
    if not input_lsp:
        input_lsp = "all"
    # print("run the command for %s" %input_lsp)

# step 1: connect and retrieve LSP and service information
    c = connect()
    # get list of all LSP, based on keys 
    LspList = c.running.get_list_keys('/nokia-state:state/router[router-name="Base"]/mpls/lsp')
    if not LspList:
        print(" no LSP found ")
    # if LSP is specified, reduce LspList to single LSP
    if input_lsp in LspList:
        # overwrite the list of LSP's with only the LSP which we want to use for the command
        LspList = [input_lsp]
    else:
        if input_lsp == "all":
            # assuming there is no LSP with the name "all" but this would not be a good name choice
            pass
            #continue
        else:
            print("LSP :", input_lsp, " not found")
            sys.exit()
    # get list of all Services
    # based on keys only, too avoid excessive memory usage
    # IP-VPN
    VpnList = c.running.get_list_keys('/nokia-state:state/service/vprn')
    # EVPN VPWS
    VpwsList = c.running.get_list_keys('/nokia-state:state/service/epipe')
    # EVPN ELAN
    EvpnList = c.running.get_list_keys('/nokia-state:state/service/vpls')

# step 2: build dictionary with LSP and tunnel-id
    # build dictionary with LSP's
    # check type sr-te or rsvp-te only
    LspListDict={}
    for lsp in LspList:
        try:
            # get LSP type
            # pce-init LSP put-of-scope
            lspType = c.running.get('/nokia-conf:configure/router[router-name="Base"]/mpls/lsp[lsp-name=%s]/type' % lsp)
            # get LSP tunneld-id
            lspTtmId = c.running.get('/nokia-state:state/router[router-name="Base"]/mpls/lsp[lsp-name=%s]/ttm-tunnel-id' % lsp)
            # index in dictioniary is ttm-tunnel-id, linked to LSP name and type
            LspListDict[str(lspTtmId)] = (str(lsp),str(lspType))
        except LookupError as e:
            # non-SR or non-RSVP, most likely multicast related (or PCE init)
            pass        

# step 3: mapping with IP-VPN
    # index in dictionary is TTM tunnel-id, linked to service-name and service-id
    VpnListDict={}
    for vpn in VpnList:
        # get all the routes per IP-VPN
        Unicastv4RouteList = c.running.get('/nokia-state:state/service/vprn[service-name=%s]/route-table/unicast/ipv4/route' % vpn)

        # check each route
        for Route in Unicastv4RouteList.values():
            # check the next-hops per route
            for Nexthop in Route["nexthop"].values():
                if "resolving-nexthop" in Nexthop:
                    for ResNextHop in Nexthop["resolving-nexthop"].values():
                        # check if there is actually a resolved next-hop present
                        if "nexthop-tunnel-id" in ResNextHop:
                            # below -if- statement builds entries in case not yet present in the dictionary
                            if str(ResNextHop["nexthop-tunnel-id"]) not in VpnListDict:
                                VpnListDict[str(ResNextHop["nexthop-tunnel-id"])] = []
                            # retrieve correct TTM tunnel-id, required to link to service name and id
                            nexthop_id = str(ResNextHop["nexthop-tunnel-id"])
                            # need to make string out of service-id
                            vpn_id = str(c.running.get("/nokia-state:state/service/vprn[service-name=%s]/oper-service-id" % vpn ))
                            # assure single occurance of LSP per VPN, since a single LSP can be used as next-hop for multiple routes in a VPN                            # check if tuple not yet present:
                            if (vpn, vpn_id) not in VpnListDict[nexthop_id]:
                                VpnListDict[nexthop_id].append((vpn, vpn_id))

# step 4: mapping with EVPN-VPWS
    # build dictionary with VPWS
    # 
    VpwsListDict={}
    # check each VPWS
    for vpws in VpwsList:
        try:    
            # get the mpls destination per service
            Destination = c.running.get('/nokia-state:state/service/epipe[service-name=%s]/bgp-evpn/mpls[bgp-instance="1"]/destinations' % vpws)
            # note that Destination can still be empty, for instance in case the VPWS is operational DOWN
            vpws_dest = Destination["non-ethernet-segment-destination"]
            #
            # for key,value in vpws is need to run over the list items in tunnel-id, being tunnel-id and transport-type
            for key, value in vpws_dest.items():
                for tunnelValue in value['tunnel-id'].values():
                    tunnelid = str(tunnelValue['tunnel-id']),str(tunnelValue['transport-type'])
                    # add tunnel-id if not yet present in the list
                    if tunnelid[0] not in VpwsListDict:
                        VpwsListDict[tunnelid[0]] = []
                    # need to get the service-id of the vpws
                    vpws_id = str(c.running.get('/nokia-state:state/service/epipe[service-name=%s]/oper-service-id' % vpws))
                    # link tunnel to service in combination with transport-type, part of tunnelid tuple
                    VpwsListDict[tunnelid[0]].append((str(vpws),tunnelid[1],vpws_id))
                    
        except LookupError as e:
            # none existing MPLS remote destination, possibly local, sr-policy or SRv6 based VPWs
            pass

# step 5: mapping with EVPN-ELAN
    # build dictionary with EVPN 
    #
    EvpnListDict={}
    # check each EVPN-VPLS
    for evpn in EvpnList:
        try:
            # get the mpls destination per service
            Destination = c.running.get('/nokia-state:state/service/vpls[service-name=%s]/bgp-evpn/mpls[bgp-instance="1"]/destinations' % evpn)
            # note that Destinations can still be empty, for instance in case the VPWS is operational DOWN
            evpn_dest = Destination["non-ethernet-segment-destination"]
            # for key,value in vpws is need to run over the list items in tunnel-id, being tunnel-id and transport-type
            for key, value in evpn_dest.items():
                for tunnelValue in value['tunnel-id'].values():
                    tunnelid = str(tunnelValue['tunnel-id']),str(tunnelValue['transport-type'])
                    # add tunnel-id if not yet present in the list
                    if tunnelid[0] not in EvpnListDict:
                        EvpnListDict[tunnelid[0]] = []
                    # need to get the service-id of the evpn
                    evpn_id = str(c.running.get('/nokia-state:state/service/vpls[service-name=%s]/oper-service-id' % evpn))
                    # link tunnel to service in combination with transport-type, part of tunnelid tuple
                    EvpnListDict[tunnelid[0]].append((str(evpn),tunnelid[1],evpn_id))
                    
        except LookupError as e:
            # none existing MPLS remote destination, possibly local, sr-policy or SRv6 based VPWs
            pass

# step 6: build the output-table
    #
    PrintResult = {}
    #in VpnListDict is the list of all LSP, with related VPN
    for Tunnel in list(LspListDict.keys()):
        # initialize print variables
        svcTuple = []
        # and extra check to see if there is a real value
        if lspName := LspListDict.get(Tunnel, []): 
            # lspTuple = name, type, ttm-id
            lspTuple = (lspName[0], lspName[1], Tunnel)
            # get the vpn's for the specific tunnel
            # tunnel_id = str(ResNextHop["nexthop-tunnel-id"])
            vpn_list_for_tunnel = VpnListDict.get(Tunnel, [])
            for vpn in vpn_list_for_tunnel:
                # svcTuple = name, type, svc-id, lspname
                svcTuple.append([vpn[0],"IP-VPN",vpn[1]])
            # list of all VPWS using the tunnel
            vpws_list_for_tunnel = VpwsListDict.get(Tunnel, [])
            for vpws in vpws_list_for_tunnel:
                svcTuple.append([vpws[0],"EVPN-VPWS",vpws[2]])
            # list of all VPLS-EVPN using the tunnel
            evpn_list_for_tunnel = EvpnListDict.get(Tunnel, [])
            for evpn in evpn_list_for_tunnel:
                svcTuple.append([evpn[0],"EVPN",evpn[2]])
            # link all the services to the LSP with LSP as key in the dictionary     
            if svcTuple:    
                PrintResult[lspTuple]=svcTuple
        else:
            pass
    # send the dictionary with LSP linked to service list to the output procedure
    PrintSvcTable(PrintResult)

if __name__ == "__main__":
    main()


