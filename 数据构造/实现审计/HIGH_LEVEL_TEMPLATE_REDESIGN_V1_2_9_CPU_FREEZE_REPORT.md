# High-Level Template Redesign V1.2.9 CPU Freeze

Status: `CPU_SOURCE_SNAPSHOT_FROZEN_F4_A_ONLY_ADAPTER_ANCHOR_CALLBACK_READY`

- Active/snapshot full suites: `710/710`; 396.22 s / 395.99 s.
- Source: 268 Python files, byte-equal, SHA-256 `a3e5500703d813ee4093be475286d69bed07647d43105da3a6c0db87c190c548`.
- Tests: 132 Python files, byte-equal, SHA-256 `7d3852fae85fcd3ac5e15065bcc5a544b7546752ec7d74dcbb08e1583125c82d`.
- Parent/registry/report payloads: `598a12f2…e8bf3` / `f42256fd…d5e5b` / `0ede5a8a…2f6779`.

V1.2.9 passes the adapter-bound `capture_anchor(scene)` callback into the F4 physical executor and tests its actual invocation. Candidate, layout, targets, thresholds, budgets and authorization boundaries are unchanged. Stage 1 and all later scopes remain unauthorized.
