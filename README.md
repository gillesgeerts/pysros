

This pySROS based CLI command is displaying the list of LSP (SR-TE or RSVP-TE) which are in use by services (IP-VPN, EVPN) as next-hop in an auto-bind destination.

Some notes:
1) input variable can be all (ENTER) or a specified LSP-name
1) only on model-driven SROS
2) not for PCE-init LSP or SR-policy. Technically possible, but out-of-scope
3) only for auto-bind resolution. SDP based next-hops out of scope (available in configuration and specific CLI commands)

Following procedure highlights the steps to be taken to get the python-script running as CLI command

## Quick start guide
* **create a python policy**  
  configuration of python-script on SROS
  
  example:
  ```
  [pr:/configure python]
  A:admin@R1# info
    python-script "lsp-map" {
        admin-state enable
        urls ["tftp://172.31.255.29/lsp-map.py"]
        version python3
    }
  ```
  In this case, R1 is a virtual SR in a containerlab environment. in case of a physical SR, the python-script is ideally present on the flash-disk (CFx:)

* **create the command-alias**  
  The creation of the CLI command is done under the system configuration
   
  example:
  ```
  [pr:/configure system management-interface cli md-cli]
  A:admin@R1# info
    auto-config-save true
    environment {
        command-alias {
            alias "lsp-autobind-map" {
                admin-state enable
                description "link lsp to service"
                python-script "lsp-map"
                mount-point "/show router" { }
                mount-point "/show router mpls sr-te-lsp" { }
            }
  ```
  The CLI command is available under the "show router" as well as "show router mpls". Mainly to indicate the SROS capabilities, not as recommendations


* **execute the command**  
  Example below to show the output of the CLI-command.

  example:
  ```
  [/]
  A:admin@R1# show router lsp-autobind-map
  which LSP you want to check ? (lsp-name or ENTER for all)  : 
  ===============================================================================
  lsp Algo0-R1-R6 of type p2p-sr-te with tunnel-id 655373 used in:
  ===============================================================================
  Service name                   Service type      Service ID
  -------------------------------------------------------------------------------
  customer-1                     IP-VPN            600
  R1-epipe-R6-srte               EVPN-VPWS         54
  ===============================================================================
  ===============================================================================
  lsp LSP_IETF_RSVP-TE_EXAMPLE of type p2p-rsvp with tunnel-id 2 used in:
  ===============================================================================
  Service name                   Service type      Service ID
  -------------------------------------------------------------------------------
  IBSF-vprn-50                   IP-VPN            50
  MVPN-RSVP-1                    IP-VPN            3000
  MVPN-TREE-SID-1                IP-VPN            3001
  MVPN-TREESIDv6-1               IP-VPN            3003
  R1                             EVPN-VPWS         53
  evpn-2000-pe1                  EVPN              2000
  ===============================================================================
  ===============================================================================
  lsp Algo0-R1-R2 of type p2p-sr-te with tunnel-id 655375 used in:
  ===============================================================================
  Service name                   Service type      Service ID
  -------------------------------------------------------------------------------
  customer-1                     IP-VPN            600
  MVPN-RSVP-1                    IP-VPN            3000
  MVPN-TREE-SID-1                IP-VPN            3001
  MVPN-TREESIDv6-1               IP-VPN            3003
  evpn-2000-pe1                  EVPN              2000
  ===============================================================================
  ```

* **tips and tricks** 
 
  check the status of the python-script:
  ```
  [/]
  A:admin@R1# show python python-script "lsp-map"

  ===============================================================================
  Python script "lsp-map"
  ===============================================================================
  Description   : (Not Specified)
  Admin state   : inService
  Oper state    : inService
  Oper state
  (distributed) : inService
  Version       : python3
  Action on fail: drop
  Protection    : none
  Primary URL   : tftp://172.31.255.29/lsp-map.py
  Secondary URL : (Not Specified)
  Tertiary URL  : (Not Specified)
  Active URL    : primary
  Run as user   : (Not Specified)
  Code size     : 2420
  Last changed  : 03/28/2025 15:54:12
  ===============================================================================
  ```

  reload the python-script (i.e. after editing)
  ```
  [/]
  A:admin@R1# tools perform python-script reload "lsp-map"
  ```

  direct execution of the python-script:
  ```
  [/]
  A:admin@R1# pyexec "lsp-map"
  ```