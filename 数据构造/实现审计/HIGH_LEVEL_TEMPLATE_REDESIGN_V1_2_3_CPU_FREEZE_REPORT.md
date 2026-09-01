# High-Level Template Redesign V1.2.3 CPU Freeze

Status: `CPU_SOURCE_SNAPSHOT_FROZEN_PRIOR_SLOT_NUMERIC_AUDIT_CORRECTED`

- Active full suite: `706/706`, 261.541 s.
- Review-snapshot full suite: `706/706`, 246.684 s.
- Active/snapshot source: 268 Python files, byte-equal, tree/source SHA-256 `078fc5fdb8be97c309c112db5d12dad4e19209d36ee9162a4e356e5fc5afb25a`.
- Active/snapshot tests: 132 Python files, byte-equal, tree SHA-256 `12529cfd51121b4eae0486b4751d492151367bc6c3e2688b111feea92d83347c`.
- V1.2.3 parent authorization SHA-256: `f5adec23a29227f61b7086db7d36798bab80d1a06d8a9dcc2e90efcaa32e4ac5`.
- V1.2.3 registry SHA-256: `c67c04f474c5b4a4f3e0b1affb31a0c989193e3563e3de4270cf9373061bb9d5`.
- r01/r02 correction-overlay SHA-256: `1079cf6825f9318059292c2cb2f94639fc0c9adccb98a6a238195931e9c714f8`.
- Machine report SHA-256: `1d9c51db78b4d0ff37509e4b5e004c1fea9ec142f331a823d24ecee8d7864fa8`.

Prior-slot preservation now compares position error and quaternion angular error using the existing target tolerances (`1e-9 m`, `1e-7 rad`). Raw quaternion-component equality is forbidden. The correction overlay reconstructs r01/r02 from immutable run3 receipts; both pass every Stage-B Gate without GPU re-execution.

Only r03–r08 require fresh GPU scopes. Candidate/rank/chain/budget/physical semantics/Gates are unchanged. Stage 1, formal 360 collection, training, H-reveal, compression, and π0.5 remain unauthorized.
