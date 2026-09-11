# F1_000013 attempt4 terminal handoff

- Result: `FAILED_INCOMPLETE`; no attempt5 is authorized.
- Physical run: fixed GPU0 `GPU-2c620e6c-9639-2022-b573-9847dfa33769`; lease 446 s; post snapshot 14 MiB, 0%, P8, no compute process.
- Three suffix planner preflights were scientifically solvable and produced artifacts, but no `branches/` directory or motion cell was created.
- Blocking evidence issue: `native_f1.py` motion-specific planner receipt omitted `evidence.planner_collision_check_source`; F1 family gate therefore reported `evidence_complete=false` while `scientific_gate_pass=true`.
- Usage: fresh 8, action 4, collection 0, solver 0, GPU lease 446 s; reserve eligibility false.
- Required next step: CPU-only code/test repair must preserve `planner_invoked=false` and honestly bind source to the sealed r_pc artifact before any newly authorized physical run. Do not edit this root receipt or promote suffix preflight traces.

Evidence: `/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/formal_entry_20260910/F1_FULL_PRODUCTION/F1_MOTION_RECOVERY_20260911/evidence/ATTEMPT4_TERMINAL_RECONCILIATION.json` (sha256 `c6cc29dd599970261b2d3fd6161bc507f24345e25b24ac01e7aebaec5f141468`), `/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/formal_entry_20260910/F1_FULL_PRODUCTION/F1_MOTION_RECOVERY_20260911/evidence/ATTEMPT4_ROOT_RECEIPT.json`, `/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/formal_entry_20260910/F1_FULL_PRODUCTION/F1_MOTION_RECOVERY_20260911/evidence/ATTEMPT4_FAMILY_SUFFIX_GATE.json`, `/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/formal_entry_20260910/F1_FULL_PRODUCTION/F1_MOTION_RECOVERY_20260911/evidence/ATTEMPT4_JOB_RECEIPT.json`, `/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/formal_entry_20260910/F1_FULL_PRODUCTION/F1_MOTION_RECOVERY_20260911/evidence/ATTEMPT4G_GPU_POST_SNAPSHOT.json`.
