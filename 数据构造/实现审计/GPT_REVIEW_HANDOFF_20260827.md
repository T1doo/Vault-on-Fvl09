# GPT review handoff：F1–F4 Stage 0 前置实现与 bounded repair

```yaml
repository: https://github.com/T1doo/Vault-on-Fvl09
branch: main
design_version: controlled_multi_future_f1_f4_v1_2
document_structure_revision: merged_master_v1
publication_content_commit: CONTENT_COMMIT_TO_BE_FILLED_AFTER_COMMIT
current_decision: BLOCKED_WITH_REASONS
stage0_authorized: false
formal_data_generated: false
```

## 1. 审阅顺序

请按以下顺序读取，不要用归档旧方案覆盖当前规范：

1. `Idea/项目核心Idea.md`：研究定义、claim boundary 与当前科学问题。
2. `数据构造/数据构造方案.md`：唯一当前 F1–F4 frozen protocol。
3. `数据构造/实现审计/bounded_repair_execution_report_20260827.md` 及 JSON：本轮最终 runtime 结论。
4. `数据构造/实现审计/stage0_readiness_report.md` 及 JSON：当前 readiness 与下一安全动作。
5. `数据构造/实现审计/f1_f4_implementation_registry_v1_current.md` 及 JSON：当前 source/asset/status registry。
6. `数据构造/实现审计/pilot_attempt_budget_v0_proposal.md` 及 JSON：仍未批准／冻结的 budget proposal。
7. `数据构造/实现审计/f2_beside_reference_pot_audit_v2.md` 及 JSON：F2 pot fallback 的官方来源和 joint-scene wrapper。
8. `数据构造/实现审计/代码审阅快照/README.md`，再读同目录 active-source byte-equal snapshot 与 tests。
9. `数据构造/实现审计/probe_outputs/` 中下列 receipts/guards/traces。
10. `数据构造/正式数据构造日志.md` 尾部 §22–§29：完整 chronology、失败保留、GPU pre/post 与停止点。

## 2. 本轮已经完成什么

- 保持科学设计不变：4 families、40 accepted roots、360 formal trajectories、3 intents/root、R=3、5/2/3 split、F3 `VVHH/VHVH/VHHV`、F4 `common-X + ABC/ACB/BAC`。
- additive active implementation 位于服务器 RoboTwin 工作树的 `controlled_multi_future/`；未修改官方 tracked baseline。
- 实现 cleanup-safe scene lifecycle、dense realized trace v2、指定执行臂 gripper-link contact、candidate freezer、current hash、anchor equivalence、26-D/250 Hz/N+1 raw writer、attempt state machine、receipt、finalizer、semantic probe Gate 和 atomic GPU guard。
- atomic GPU guard 在每个 child 前检查 physical index/UUID/memory/utilization/P-state/compute process，记录 PID/PGID，执行 timeout，回填 postcheck，并审计 orphan。
- active source 与 Vault snapshot 均 20/20 tests passed，34 Python files compile，逐文件 diff 零差异。
- synthetic pipeline integration 通过 candidate/task-tree/prefix freeze、两个 fresh adapter lifecycles、same-current、anchor、raw save、verifier、cleanup/orphan 与 finalizer；它明确不是 SAPIEN runtime evidence。
- 执行所有用户批准的 bounded F1/F2/F3 repairs、F2 pot fallback 和 F4 第一 ordered Gate；失败全部保留。
- GPU safety summary：12 个真实 child runs、4 个 precheck blocks、0 timeout、0 scene cleanup failure、0 task-owned orphan。

## 3. Family 最终 runtime 结果

### F1

- `fp1`：planner 完成，非目标稳定，但目标 block 最终不 inside。
- `interior`：OBB inside=true，但 green/blue displacement=`0.05633/0.01967 m`。
- 两个 bounded variants 均未通过 `inside + non-target stability + gripper/retract` 完整 Gate；F1 unresolved。
- 重要：`fp1` 的早期 receipt 因旧代码只看 `plan_success` 写成 passed；最终机器／人工 semantic review 已在 bounded report 明确裁决为失败。审阅时不得把该旧 status 当最终结论。

Receipts：

- `probe_outputs/f1_block_inside_box_repair_v1_fp1_20260827_attempt2_tracefix/receipt.json`
- `probe_outputs/f1_block_inside_box_repair_v1_interior_20260827/receipt.json`

### F2

- 固定同一 `071_can/base1 + left arm`；历史 inside/on 通过。
- display-stand `sector1`、`sector2` 均 place planner failure。
- 按预定 fallback 审计并运行官方 `060_kitchenpot/base0` reference；官方原 task 的 can 是不同 `105_sauce-can`，本项目没有换 main object。
- `pot_left` 仍 place planner failure；所有授权 beside references 用尽，F2 unresolved。

Receipts：

- `probe_outputs/f2_beside_clearance_repair_v1_sector1_20260827_attempt2_tracefix/receipt.json`
- `probe_outputs/f2_beside_clearance_repair_v1_sector2_20260827/receipt.json`
- `probe_outputs/f2_beside_reference_pot_audit_v2_pot_left_20260827_gpu5_run1/receipt.json`

### F3

- table-z V / table-x H realized motion 核心仍成立。
- `pad_center` 失败于 return pre-place planner。
- `bottle_fp` planner 全完成；V/H selected-gripper contact fraction=1.0、break=0，但 final bottle position/orientation/rest errors=`0.25152 m / 0.99689 / 0.38621 m`，semantic failure。
- 两个 return variants 用尽；不得把 V/H core success 升级为完整 F3 success。

Receipts：

- `probe_outputs/f3_return_pad_repair_v1_1_pad_center_central_restore_20260827/receipt.json`
- `probe_outputs/f3_return_pad_repair_v1_bottle_fp_20260827_gpu5_run1/receipt.json`

### F4

- 历史 yellow-X visibility 与 single A neutral block 通过。
- 本轮 F4-01 `common X → tray → neutral` 失败于 `place_common_X` planner。
- 按 ordered Gate，B-only、C-only、common-X+AB、ABC、ACB、BAC 和 strict reorder 均未运行；这不是缺失日志，而是预定 stop-on-first-failure 行为。

Receipt：

- `probe_outputs/f4_full_program_probe_v1_common_20260827_gpu5_run1/receipt.json`

## 4. 代码审阅重点

请重点判断以下问题属于 collector implementation、joint-scene geometry/reachability、primitive mapping，还是需要经批准的新 implementation version；不要直接改变科学设计：

1. F1 interior path 为何会移动非目标 blocks；检查 arm/transport sweep、初始动态稳定、collision envelope 与 verifier 的 initial sampling 时点。
2. F2 为何同一 can 的 inside/on 可行，而 stand 两 sectors 和 pot_left 都在 place planning site 失败；检查 joint-scene obstacles、target orientation、left-arm reach、pre-dis axis 与 target center definition。
3. F3 bottle_fp 为何 planning/release 完成但瓶子最终偏移、姿态和 arm rest error 极大；检查 functional-point transform、release orientation、reverse-control replay、actor-vs-EEF offset 与 post-release dynamics。
4. F4 common-X→tray 为什么在 place planner 失败；检查 tray scale/functional point、left-arm cross-workspace reach、common-X object choice、neutral pose 与 project joint-scene layout。
5. `gpu_guard.py`、`lifecycle.py`、`runtime_trace.py`、`pilot_pipeline.py` 是否满足 fail-closed、ownership-scoped cleanup 和 raw-first contract。
6. 当前 synthetic pipeline 是否仍缺真实 SAPIEN fresh-scene current/anchor integration；不能用 synthetic pass 代替。

## 5. 希望 GPT 给出的明确结论

请输出：

1. 是否同意当前 readiness 只能是 `BLOCKED_WITH_REASONS`。
2. F1–F4 每个 blocker 的最可能根因排序及直接代码证据。
3. 一个 additive、有限、可审计的下一 implementation version proposal；列出哪些改动不改变科学设计，哪些需要 impact review/用户批准。
4. 新 probe 前必须增加的 CPU tests、static geometry checks 与 verifier checks。
5. 是否存在任何 receipt/status/threshold/trace 误读或 claim overreach。
6. `pilot_attempt_budget_v0` 是否仍应保持 `proposed_for_user_review / approved=false / frozen=false`。
7. 下一轮仍不得启动 Stage 0，除非新的 runtime evidence 满足 readiness Gate。

## 6. 禁止误读

- 这些都是 `formal_data=false / stage0_data=false` 的 implementation probes，不计入 12、48 或 360 分母。
- 没有 Stage 0、Stage 1、formal collection、机制模型训练、VLA、compression 或 π0.5 训练。
- 12 个 child 均已 cleanup，task-owned orphan=0。
- Vault 的 `代码审阅快照/` 是 active source 的 byte-equal snapshot；实际继续开发仍应发生在服务器 RoboTwin active source，不能在快照中分叉。
- 当前没有 commit/push 以外的外部状态变更授权；不要建议通过杀其他用户进程、显存占位或修改系统 GPU compute mode 获取独占。
