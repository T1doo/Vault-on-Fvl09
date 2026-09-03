# Post-recovery external review decision V1

日期：2026-09-03  
来源：`https://chatgpt.com/s/t_6a997c5470908191b3c9135c6aada44f`  
审阅的 Vault HEAD：`2ea4625ffc83fc57b4365e682a97a4bfa2c1c6fc`  
审阅的 controlled source SHA-256：`cb4cb3b1058f8296febddae5eeb261fa2b9c413187d50cbf45d7de6538af8a43`

## 明确决定

- F2：`APPROVE_AS_PROPOSED`。严格使用已提案的 top-contact-only 筛选、最低 `(contact_id, rotation_index)` 成功姿态冻结、闭爪前 5 mm / 0.05 rad tracking 硬门；planner 上限 44，physical candidate 上限 4。
- F3：`APPROVE_AS_PROPOSED`。只运行四个已冻结 rotation1 tuple，Stage B 以 Stage-A 实际 lift pose 为 event center；planner 上限 40，physical candidate 上限 4；只有至少两个physical success后，才允许一次 same-prefix × 3 fresh scenes × no-suffix diagnostic。
- F4：`REOPEN_EXACTLY_ONCE`。只允许一个 development-root replacement；必须绑定上述 controlled source SHA 和 `f4_full_program_physical_v1.py` SHA-256 `f9f12de9f23e784fa1fa600aaa3b9e2ac27e4226d3fea8b84c466230a4f67ea8`，复用 Run9/Run12 的原 candidate/layout/seed/current/anchor/arm/program/verifier/threshold contract，禁止搜索、改布局、改阈值或改 program。

## F4 唯一重开资源上限

- one canonical-prefix generation and freeze；
- three exact prefix replays；
- at most three suffix preflights；
- at most three branch executions；
- planner queries `<=136`；
- fresh scenes `<=8`；
- robot-action scenes `<=4`；
- debug MP4 `<=3`；
- accepted development roots `<=1`；
- accepted development trajectories `<=3`；
- formal trajectories `=0`。

Run12 `total_before` 问题必须先通过直接调用 `plan_f4_full_program_suffix_from_replayed_prefix_v1` 的 production-path regression。任一 source/hash/authorization/Guard/current/anchor/prefix/planner/accounting/implementation/physical/verifier 失败必须立即停止；禁止 fallback、automatic retry、第二个 replacement 或自动继续。

## 未授权边界

`Stage0_rerun=false`，`Stage1_authorized=false`，`formal360_authorized=false`，`training_authorized=false`，`H_reveal_authorized=false`，`compression_authorized=false`，`pi05_authorized=false`。只允许 fvl05 上启动时独立 fresh-idle 的 physical GPU0–7，并继续执行每 job 的 Guard/UUID/lease/pre-post/cleanup 审计。

旧 `PROPOSED_NEXT_GATE_MANIFEST_V1.json` 保持 `approved=false/executable=false`，不改写；后续只能新建版本化、绑定本决定的授权与运行产物。
