# F1–F4 Stage 0 前置修复报告（2026-08-27）

> 本文件记录 GPU repairs 执行前的阶段性状态。后续实际执行结果以 `bounded_repair_execution_report_20260827.{md,json}` 和最新 `stage0_readiness_report.{md,json}` 为准；不要把下文“尚未运行”当成当前状态。

## 总状态

`BLOCKED_WITH_REASONS`

本轮完成了 CPU 侧实现修复、versioned repair 设计、Stage-0-shaped 最小管线和 synthetic integration；GPU4–7 在两次 fresh Gate 中均有外部任务，因此没有安全启动任何新 action repair 或 F4 program probe。

| Family | 本轮新增 | 完整跑通 | 仍缺 |
|---|---|---|---|
| F1 | `fp1/interior` bounded repair、OBB/非目标位移 verifier | 否 | 三个 RGB block 均需真实 block→box 成功；本轮未运行 |
| F2 | 同 `071_can/base1`/left 的两个 stand sectors 与 exclusive predicate scaffold | 否 | beside 真实成功；stand 两 sector 均失败后才可审计 pot |
| F3 | 分段 world-z return、2-query return path、EEF+bottle+selected-gripper trace | 否 | return-to-pad 真实成功与稳定释放 |
| F4 | common/A/B/C/common-AB/ABC/ACB/BAC 顺序 runner 与 noninterference trace | 否 | 所有自然程序真实成功；strict reorder 当前不具备条件 |

## 数据管线

已实现并 CPU-tested：candidate freezer、current hash、anchor、fresh-lifecycle interface、raw writer、26-D/250 Hz/N+1 contract、receipt、verifier adapters、finalizer、cleanup/orphan audit。synthetic dry-run receipt=`accepted`，但 `formal_data=false / stage0_data=false / synthetic_only=true`；真实 SAPIEN fresh-scene integration 仍缺。

## Budget

`pilot_attempt_budget_v0` 仍为 `proposed_for_user_review / approved=false / frozen=false`。四类 count semantics、Stage 0/Stage 1 root budget、单次 slot-spec generation 与 fresh reconstruction 已补齐；repair/F4 完整程序没跑完前不建议批准 wall-time、planner-query 总量或 GPU-hour 数字。

## GPU blocker

- 19:27：GPU4–7 均有外部 compute jobs，利用率 `72/99/65/100%`。
- 19:30：仍均有外部 compute jobs，利用率 `65/75/94/100%`。
- task-owned GPU process 始终为 0；未共享、未切到 GPU0–3、未干预外部进程。

## 禁止项确认

本轮没有 Stage 0、Stage 1、360 条正式数据、模型训练、compression 或 π0.5 训练。
