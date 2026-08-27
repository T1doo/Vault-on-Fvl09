# Nonformal probe boundary

Probe implementations added here must write only to:

`/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/probe_outputs/`

Every receipt must set `formal_data=false`, `stage0_data=false`, use purpose
`implementation_audit` or `nonformal_feasibility`, and declare a finite timeout
and attempt limit no larger than three. This directory currently contains no
GPU/runtime probe script; GPU0 was busy during the static audit.
