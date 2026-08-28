# F1–F4 runtime-v2 current registry

当前实现版本是 `controlled_multi_future_runtime_v2`，科学设计仍是 `controlled_multi_future_f1_f4_v1_2`。本文件继承 `f1_f4_implementation_registry_v1_current.json` 中已经核实的官方代码、资产和物理属性，只更新当前实现与运行状态。

| Family | runtime-v2 修复 | CPU/static | 新 GPU runtime | 当前状态 |
| --- | --- | --- | --- | --- |
| F1 | 高位运输、actor→EEF、semantic cavity/free-core、box support、full-rest、非目标位移 | 红分支全部通过 | GPU1 PASS | 仅红分支 supported；绿/蓝未运行 |
| F2 | `071_can/base1 + left arm + stand`；真实 planner preflight | 三个姿态几何通过、planner 全 Fail | GPU1 FAIL | terminal blocker |
| F3 | exact actor return；realized EEF+bottle V/H；actual rest | V/H 全通过，final pose 失败 | GPU1 FAIL | terminal blocker |
| F4 | common-X actor→EEF；高位路径；tray/neutral Gate | safe-horizontal planner 失败 | GPU1 FAIL | common 未完成；后续未运行 |

公共 trace/raw 合同已修正：effective/requested/planner target 分流，完整双臂 qpos/qvel 与双 EEF，quaternion angular velocity，逐字段 source/status，以及明确的 26-D 顺序。runtime trace 已能转换为 N actions / N+1 states；raw writer 还强制 N+1 object/contact audit 与精确 250 Hz cadence。GPU guard v2 对 pre/post snapshot 和 baseline release 均 fail closed。

当前 bounded probe round 已完成，完整报告见 `runtime_v2_bounded_probe_execution_report_20260828.md/json`。所有实际 family runs 均 cleanup=true、orphan=0、post-release verified；没有 retry。旧 bounded repair 失败仍保留。

结论仍为 `BLOCKED_WITH_REASONS`：1 个红分支 pass 不满足 F1 三分支要求，F2/F3/F4 均有 terminal blocker，真实 SAPIEN fresh-scene pipeline integration 也未完成。
