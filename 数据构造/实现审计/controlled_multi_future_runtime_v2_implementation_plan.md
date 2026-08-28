# controlled_multi_future_runtime_v2 实现计划

当前状态：`bounded_probe_round_complete_with_blockers`。四条 probes 已在 GPU1 顺序完成：F1 红分支通过；F2 planner preflight 全失败；F3 V/H 通过但 return-equivalence 失败；F4 safe-horizontal planner 失败。当前版本没有 retry budget。Stage 0 与正式采集未授权。

科学设计没有变化，仍是 `controlled_multi_future_f1_f4_v1_2`：4 families、40 roots、360 trajectories、每 root 3 intents × R=3、5/2/3 split，F3/F4 程序保持原样。

## 本版修复

| Family | 实现版本 | 修复内容 | 下一条有限 probe |
| --- | --- | --- | --- |
| F1 | `f1_transport_and_true_inside_v2` | settle baseline；高位路径；actor→EEF；semantic cavity/free-core 分离；box support；最终 rest 后稳定窗口；逐阶段非目标位移 | `transport_true_inside`，1 次执行，最多 12 次 planner query |
| F2 | `f2_actor_to_eef_beside_mapping_v3` | 固定 `071_can/base1 + left arm + stand`；3 个 yaw；真实 planner preflight；exclusive beside/support；最终 full-rest/stationarity | `actor_to_eef_stand`，1 次执行，最多 12 次 planner query |
| F3 | `f3_return_equivalence_v2` | exact actor pose；world-z；actual rest；realized EEF+bottle V/H；最终 orientation/rest/pad-support/stationarity | `return_equivalence`，1 次执行，最多 18 次 planner query |
| F4 | `f4_common_prefix_mapping_v2` | common-X actor→EEF；高位路径；tray footprint/support；A/B/C 分阶段位移；完整 neutral pose/velocity/gripper 边界 | 只运行 `common_prefix_mapping`，1 次执行，最多 12 次 planner query |

旧 `action_feasibility.py` 已作为历史实现 fail-closed 禁止重跑；新 runner 是 `action_feasibility_v2.py`。

## 公共数据合同修复

- 26-D 顺序冻结为：left position 0–5、right position 6–11、left velocity 12–17、right velocity 18–23、left/right gripper 24–25。
- effective、requested、planner target 不再用同一个副本冒充；每个流都有 `source/status`。
- realized state 保存完整双臂 qpos/qvel 与双臂 EEF；EEF angular velocity 从 quaternion 差分得到。
- runtime trace 可转换为 N actions / N+1 states；row 0 是真实 pre-action state。
- child 启动后若没有 receipt，GPU guard 终止为 `failed_missing_child_receipt`；pre/post snapshot 失败或显存、利用率、进程未回 baseline 也会 fail closed，ownership 不确定的进程不会被杀。
- Raw audit 强制保存 N+1 object pose/contact count、逐字段 source/status，并验证精确 250 Hz timestamps。

## 授权边界

本轮可在 physical GPU0–7 中任一 independently fresh-idle 卡上，以即时 UUID 绑定、单卡单 job、全局顺序方式运行四个独立 nonformal probes。每个 family 只有一个 execution attempt；不自动重试。F4 common-X 不通过时，不运行 A/B/C 或 ABC/ACB/BAC。授权及 scope update 分别见 `runtime_v2_probe_authorization_receipt_20260828.json` 与 `runtime_v2_probe_authorization_scope_update_20260828.json`。

该批准不包含 Stage 0、Stage 1、360 条正式数据、训练、compression 或 π0.5。

当前机器证据见 `runtime_v2_cpu_static_audit_20260828_v3.json`、`runtime_v2_completion_audit_20260828.md/json`、cpu2 synthetic pipeline receipt、F1 semantic adjudication、F2 pot supersession 和 `代码审阅快照/`。早期 static audits 保留为历史证据；v3 是 current。最终 readiness 仍是 `BLOCKED_WITH_REASONS`。
