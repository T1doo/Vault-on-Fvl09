# Nonformal probe boundary

Probe implementations added here must write only to:

`/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/probe_outputs/`

Every receipt must set `formal_data=false`, `stage0_data=false`, use purpose
`implementation_audit` or `nonformal_feasibility`, and declare a finite timeout
and attempt limit no larger than three. This directory currently contains no
formal or Stage-0 collector.

`action_feasibility.py` is the preserved bounded-repair v1 implementation and
must not be rerun. `action_feasibility_v2.py` is the reviewed
`controlled_multi_future_runtime_v2` implementation. It may use any physical
GPU0--7 that independently passes the immediate fresh-idle guard, requires the
explicit approval flag, uses one card at a time, and uses one immutable attempt
namespace. The user has authorized exactly one bounded nonformal probe
for each F1--F4 runtime-v2 family; this does not authorize retries, Stage 0, or
formal collection. CPU/static tests
and the synthetic pipeline may run without that GPU authorization, but their
outputs do not establish SAPIEN feasibility or Stage-0 readiness.
