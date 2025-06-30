

This pySROS based CLI command is displaying the list of GRPC based telemtry subscriptions. by SROS MD-CLI, this would require the execution of multiple commands. The script will simplify this by having single command to execute.

Some notes:
1) no input variables required
1) only on model-driven SROS

Following procedure highlights the steps to be taken to get the python-script running as CLI command

## Quick start guide
* **create a python policy**  
  configuration of python-script on SROS
  
  example:
  ```
  [pr:/configure python]
  A:admin@R1# info
    python-script "streaming-subscriptions" {
        admin-state enable
        urls ["tftp://172.31.255.29/stream-subscriptions.py"]
        version python3
    }

  ```
  In this case, R1 is a virtual SR in a containerlab environment. in case of a physical SR, the python-script is ideally present on the flash-disk (CFx:)

* **create the command-alias**  
  The creation of the CLI command is done under the system configuration, based on defining a command-alias
   
  example:
  ```
  [pr:/configure system management-interface cli md-cli]
  A:admin@R1# info
    auto-config-save true
    environment {
        command-alias {
            alias "stream-subscriptions" {
                admin-state enable
                description "show the streaming telemetry subscriptions, excluding the on-change subscriptions"
                python-script "streaming-subscriptions"
                mount-point "/show system telemetry grpc" { }
            }

  ```
  The CLI command is available under the "show system telemetry grpc"


* **execute the command**  
  Example below to show the output of the CLI-command.

  example:
  ```
  A:admin@R1# show system telemetry grpc stream-subscriptions 
  total subscription list : [1, 2, 3, 4, 5]
  ===============================================================================
  of which the following are gRPC streaming telemetry subscriptions
  ===============================================================================
  Id    path                                                                    
  -------------------------------------------------------------------------------
  1     /state/router[router-name=Base]                                         
            /interface[interface-name=*]/if-attribute/delay                     
                                                                                
  2     /state/router[router-name=Base]                                         
            /interface[interface-name=*]/statistics/ip                          
                                                                                
  3     /state/port[port-id=*]/statistics                                       
  4     /state/router[router-name=Base]                                         
            /interface[interface-name=*]/statistics/mpls                        
                                                                                
  5     /state/router[router-name=*]                                            
            /mpls/statistics/lsp-egress[lsp-name=*]                             
            /lsp-path[path-name=*]                                              
  -------------------------------------------------------------------------------
  No. of Subscriptions: 13
  ===============================================================================

  ```

* **tips and tricks** 
 
  check the status of the python-script:
  ```

  A:admin@R1# show python python-script "streaming-subscriptions" 

  ===============================================================================
  Python script "streaming-subscriptions"
  ===============================================================================
  Description   : (Not Specified)
  Admin state   : inService
  Oper state    : inService
  Oper state      
  (distributed) : inService
  Version       : python3
  Action on fail: drop
  Protection    : none
  Primary URL   : tftp://172.31.255.29/stream-subscriptions.py
  Secondary URL : (Not Specified)
  Tertiary URL  : (Not Specified)
  Active URL    : primary
  Run as user   : (Not Specified)
  Code size     : 907
  Last changed  : 04/24/2025 09:52:16
  ===============================================================================

  ```

  reload the python-script (i.e. after editing)
  ```
  A:admin@R1# tools perform python-script reload "lsp-map" 

  ```

    direct execution of the python-script:
  ```
  A:admin@R1# pyexec "streaming-subscriptions" 
   total subscription list : [1, 2, 3, 4, 5]
   ===============================================================================
   of which the following are gRPC streaming telemetry subscriptions
   ===============================================================================
   Id    path                                                                    
   -------------------------------------------------------------------------------
   1     /state/router[router-name=Base]                                         
             /interface[interface-name=*]/if-attribute/delay                     
                                                                                 
   2     /state/router[router-name=Base]                                         
             /interface[interface-name=*]/statistics/ip                          
                                                                                  
   3     /state/port[port-id=*]/statistics                                       
   4     /state/router[router-name=Base]                                         
             /interface[interface-name=*]/statistics/mpls                        
                                                                                  
   5     /state/router[router-name=*]                                            
             /mpls/statistics/lsp-egress[lsp-name=*]                             
             /lsp-path[path-name=*]                                              
   -------------------------------------------------------------------------------
   No. of Subscriptions: 13
   ===============================================================================

  ```