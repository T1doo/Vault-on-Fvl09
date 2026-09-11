# F1 全族真实生产：GPT 独立审阅交接

**状态：`PAUSED_FOR_GPT_REVIEW`**

本文件用于独立审阅。物理执行已暂停；不应从本文件直接恢复 GPU。当前 F1 任务在冻结的四个 reserve 耗尽后保持 `FORMAL_DATASET_INCOMPLETE`。

## 审阅边界

- 范围只包含 F1；F2/F3/F4、训练、H-reveal、compression、HD 渲染均未启动。
- 不覆盖或重写旧 raw、失败记录、STATE、ledger、接受历史。
- 本轮物理运行使用的 source bundle：`2309842186c73b51515f910bee7423058ce0311da561f275d3dda9ea00712460`。
- 暂停后发现的候选 UTF-8 修复使当前工作树 bundle 变为 `d090d16b32621e32958ffe06cc91cb44876bb706e6dd1a93ba9fc370d08dcbe6`；它没有用于本轮物理运行，现仅作为候选供审阅。

## 已确认结果

| 项目 | 结果 |
|---|---|
| 完整 9-cell root | **0** |
| 保留且独立重验通过的真实 cell | **14**（F1_000011: 6，F1_000012: 2，F1_000013: 6） |
| 研究资格 | 未形成完整可用 F1 root |
| launcher 实际累计 | `{'action_scenes': 65, 'collection_attempts': 18, 'fresh_scenes': 121, 'gpu_lease_seconds': 7283, 'solver_problems': 495}` |
| family 状态 | `FORMAL_DATASET_INCOMPLETE`，blocking=`[{'reason': 'four ordered reserves exhausted'}]` |
| compatibility appendix | `/nfs_share/lijunhui/Robotwin2/datasets/f1_runtime_compat_v3_utf8b/F1_RUNTIME_COMPATIBILITY_APPENDIX.json`，sha256=`e83d96eac5699f985a804e5632cbc9f7f32a6729111b9f04a94be4e86ce8f918` |

## 每个 root 的结论

| root | attempts | 结论 |
|---|---:|---|
| F1_000001 | 2 | 真实 target_lift IK 不可行；bounded recovery 后仍失败。 |
| F1_000002 | 2 | 两次 transient startup failure；未形成物理 cell。 |
| F1_000011 | 2 | r_pc/path 各 3 条保留；motion cohort 失败，root 不完整。 |
| F1_000012 | 2 | r_pc red/green 共 2 条保留；其余未形成完整 root。 |
| F1_000013 | 2 | r_pc/path 各 3 条保留；motion cohort 失败，root 不完整。 |
| F1_000014 | 2 | 第一次 r_pc red 被独立 verifier 拒绝；第二次 recovery 在物理前因 current/anchor/prefix 不一致退出；最后 reserve 耗尽. |

## F1_000014 关键证据

- 第一次 `r_pc` 只执行了 F1-red 分支；动作阶段的物理检查大部分通过，但 `green_max_displacement_m=0.007002989587648229`，超过 `non_task_position_m=0.003`，因此 `failed_verifier`。blue 位移约 `6.55e-7 m`。
- 第二次 recovery 没有执行物理 branch：`recovery_2/root/root_receipt.json` 的错误是 `recovery actual regenerated prefix/current/anchor differs`。这说明严格复用检查拒绝了新的 t0/current/anchor/prefix，不能把它当作成功或同一 root 的可复用数据。
- 两次 attempt 均 `owned_cleanup_pass=true`、`release_confirmed=true`；最终 GPU0 回到约 14 MiB、0%、P8、无 compute process。

## CPU 代码与审计状态

- 已提交远端的实现/收口 commits：`773bcca`（入口编码与 motion runtime 修复）、`32a5e2f`（最终不完整状态和日志）。
- 20 项 `test_family_entry.py + test_first_wave_launcher.py` 回归在候选 UTF-8 修改后全部通过；ASCII locale 中文回执 round-trip 通过；py_compile 通过。
- 当前工作树仍有候选修改：`native_f1.py`、`native_f1_orchestrator.py` 的 JSON 读写显式 UTF-8。它们未绑定到已用的 v3 appendix，也未用于 F1_000014 物理 run。
- current/anchor/prefix 的跨 root CPU 对账显示：F1_000011 与 F1_000013、F1_000012 与 F1_000014 均不是 byte-identical，因此不能把这些 partial cells 拼接或互换成完整 root。

## 请 GPT 重点裁决

1. `FORMAL_DATASET_INCOMPLETE` 是否应作为本轮终态保留，并禁止通过改状态或改 verifier 重新计数。
2. F1_000014 的 `green` 非任务扰动，应优先通过调整目标运输/场景布局解决，还是直接淘汰该 scene；哪些改动仍属于动作实现修复，哪些已构成新 scientific scene contract。
3. recovery current/anchor/prefix 不一致时，是否保持严格拒绝，并为新鲜场景建立新 root；不要放宽为“相似即可复用”。
4. 下一轮若要完成 10 个有效 root，应建立多少新的 primary/reserve、独立 manifest/ledger/budget；不得沿用本账本余额，也不得把 14 个 partial cell 当作完整 root。
5. 候选 UTF-8 修改是否应合入下一轮 source freeze；若合入，应重新生成兼容 appendix 和 CPU evidence，不能继续使用 v3 source bundle。

## 证据入口

- [最终 F1 状态报告](/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/formal_entry_20260910/F1_FULL_PRODUCTION/F1_FULL_PRODUCTION_FINAL_STATUS_20260911.json)
- [F1 launcher STATE](/nfs_share/lijunhui/Robotwin2/datasets/formal_f1_full_v1_state/launcher/STATE.json)
- [F1 FAMILY_STATE](/nfs_share/lijunhui/Robotwin2/datasets/formal_f1_full_v1_state/FAMILY_STATE.json)
- [已用 v3 compatibility appendix](/nfs_share/lijunhui/Robotwin2/datasets/f1_runtime_compat_v3_utf8b/F1_RUNTIME_COMPATIBILITY_APPENDIX.json)
- [F1 日常构造日志](/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/F2F3重设计与构造日志.md)

本轮暂停后不启动 GPU；任何继续执行都必须先经过 GPT 审阅，再建立新的、独立的合同/预算/STATE。
