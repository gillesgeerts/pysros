# pysros
List of PySROS based CLI commands

# quick overview of commands

1) telemetry paths
    helps in visualizing the paths in case streaming telemetry is active on the node. this may require 2 cli command executions, with this CLI command it limits to a single one
2) lsp-autobind-map
    gives an overview of services (evpn/vprn) which rely on auto-bind tunneling and highlights the LSP's that are currently in use
3) show-binding-sids
    lists all the binding-sids that are available on the node, operational or not. the binding sids could be linked to SR-policies and SR-TE LSP