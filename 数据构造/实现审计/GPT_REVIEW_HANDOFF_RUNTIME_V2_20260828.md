# GPT 审阅入口：F1–F4 runtime-v2 bounded probes

## 如何定位

- GitHub repository：`https://github.com/T1doo/Vault-on-Fvl09`
- Branch：`main`
- 本轮 content commit：`3a98c079930e3c7f12b9633893b152db09156d07`
- 科学设计：`controlled_multi_future_f1_f4_v1_2`
- 实现版本：`controlled_multi_future_runtime_v2`
- 当前裁决：`BLOCKED_WITH_REASONS`
- `stage0_authorized=false`

请先读本文件，再按下面顺序读取证据。不要把旧 bounded repair、CPU synthetic pass 或单个成功分支解释成 Stage 0 ready。

## 一、必须先读

1. `Idea/项目核心Idea.md`
2. `数据构造/数据构造方案.md`
3. `数据构造/实现审计/runtime_v2_bounded_probe_execution_report_20260828.md`
4. `数据构造/实现审计/stage0_readiness_report_runtime_v2_current.md`
5. `数据构造/实现审计/f1_f4_implementation_registry_v2_runtime_current.md`
6. `数据构造/实现审计/controlled_multi_future_runtime_v2_implementation_plan.md`
7. `数据构造/实现审计/pilot_attempt_budget_v0_runtime_v2_addendum.md`
8. `数据构造/正式数据构造日志.md` 的 §33–§42

机器可读版本均位于同名 `.json` 文件。

## 二、这轮准确完成了什么

### 公共实现

- actor pose → EEF pose 的 frozen-grasp transform；
- F1 semantic cavity 与 collision-free descent core 分离；
- F1/F4 分阶段 non-target displacement；
- F2 三个预注册 upright yaw 的真实 planner preflight；
- F3 realized EEF+bottle V/H、selected-arm contact 与 exact return/rest Gate；
- F4 common-X support/noninterference/full-neutral boundary Gate；
- effective/requested/planner target 分流；
- 完整双臂 qpos/qvel、双 EEF、quaternion angular velocity；
- 明确的 26-D layout、250 Hz、N actions/N+1 states；
- 强制 N+1 object/contact audit streams 与 source/status；
- GPU guard v2：fresh-idle/UUID、timeout、process group、missing receipt、pre/post snapshot、baseline release、orphan audit；
- guard child 固定 workspace CUDA 12.1，不继承 host CUDA 12.2；
- active source 与 Vault snapshot byte-equal，32/32 CPU tests passed。

这些代码仍是 additive implementation，官方 RoboTwin tracked baseline `c3ddfa8b97d5519efa828b075999bd0006778e5e` 未修改。Active source 没有 commit/push；GitHub 只发布 Vault 中的审阅快照。

## 三、四个 Family 的最终结果

| Family | 终态 | 机器结论 |
| --- | --- | --- |
| F1 | `passed_nonformal_action_probe` | 红方块 true-inside、连续 box support、绿/蓝全阶段稳定、gripper/rest/stationarity 全通过；只证明红分支，绿/蓝目标分支未运行 |
| F2 | `aborted_with_reason` | 同一 `071_can/base1 + left arm + 074_displaystand/base3`；三个预注册 yaw 都通过 geometry，但真实 planner preflight 全部 `Fail` |
| F3 | `failed_nonformal_action_probe` | realized V/H 全通过，contact fraction=1.0、break=0；最终 bottle position/orientation errors=`0.04096 m/0.15587`，return-equivalence 失败 |
| F4 | `failed_planner` | swept geometry 通过，但 `safe_horizontal_waypoint` planner 失败；按 ordered Gate 未运行 A/B/C、ABC/ACB/BAC |

因此这轮是“1 个红分支 pass / 3 个 family terminal blockers”，不是“F1–F4 跑通”。

## 四、必须检查的 receipts/traces

### F1

- 环境导入失败（execution=0，不消耗 family attempt）：
  - `数据构造/实现审计/probe_outputs/f1_transport_and_true_inside_v2_20260828_gpu1_run1/receipt.json`
  - `数据构造/实现审计/probe_outputs/f1_transport_and_true_inside_v2_20260828_gpu1_run1_guard.json`
- 实际成功 attempt：
  - `数据构造/实现审计/probe_outputs/f1_transport_and_true_inside_v2_20260828_gpu1_run2_envfix/receipt.json`
  - `数据构造/实现审计/probe_outputs/f1_transport_and_true_inside_v2_20260828_gpu1_run2_envfix/trace.npz`
  - `数据构造/实现审计/probe_outputs/f1_transport_and_true_inside_v2_20260828_gpu1_run2_envfix_guard.json`

### F2

- `数据构造/实现审计/probe_outputs/f2_actor_to_eef_beside_mapping_v3_20260828_gpu1_run1/receipt.json`
- `数据构造/实现审计/probe_outputs/f2_actor_to_eef_beside_mapping_v3_20260828_gpu1_run1/trace.npz`
- `数据构造/实现审计/probe_outputs/f2_actor_to_eef_beside_mapping_v3_20260828_gpu1_run1_guard.json`

### F3

- `数据构造/实现审计/probe_outputs/f3_return_equivalence_v2_20260828_gpu1_run1/receipt.json`
- `数据构造/实现审计/probe_outputs/f3_return_equivalence_v2_20260828_gpu1_run1/trace.npz`
- `数据构造/实现审计/probe_outputs/f3_return_equivalence_v2_20260828_gpu1_run1_guard.json`

### F4

- `数据构造/实现审计/probe_outputs/f4_common_prefix_mapping_v2_20260828_gpu1_run1/receipt.json`
- `数据构造/实现审计/probe_outputs/f4_common_prefix_mapping_v2_20260828_gpu1_run1/trace.npz`
- `数据构造/实现审计/probe_outputs/f4_common_prefix_mapping_v2_20260828_gpu1_run1_guard.json`

所有实际 family runs 均：`formal_data=false`、`stage0_data=false`、cleanup succeeded、orphan=0、timeout=0、post-release verified。GPU1 每次回到 14 MiB、无 compute process。

## 五、代码审阅

代码快照：

`数据构造/实现审计/代码审阅快照/`

重点文件：

- `controlled_multi_future/geometry.py`
- `controlled_multi_future/runtime_v2_contracts.py`
- `controlled_multi_future/probes/action_feasibility_v2.py`
- `controlled_multi_future/probes/runtime_trace.py`
- `controlled_multi_future/probes/gpu_guard.py`
- `controlled_multi_future/raw_writer.py`
- `controlled_multi_future/pilot_pipeline.py`
- `tests/controlled_multi_future/`

CPU/static current：

- `数据构造/实现审计/runtime_v2_cpu_static_audit_20260828_v5_any_gpu.json`
- `数据构造/实现审计/runtime_v2_completion_audit_20260828.md/json`
- synthetic raw current：`数据构造/实现审计/probe_outputs/nonformal_pipeline_dry_run_runtime_v2_20260828_cpu2/`

注意：synthetic pipeline 只证明软件合同；真实 SAPIEN fresh-scene current/anchor/raw/verifier/finalizer integration 尚未运行。

## 六、希望 GPT 重点裁决

请不要直接批准 Stage 0。请先回答：

1. F1 红分支成功是否足以确认 transport/cavity implementation 基本正确？绿/蓝扩展应采用什么新 implementation version 和最小 finite budget，才能证明三分支而不形成 success-only selection？
2. F2 三个 target-actor yaw 都几何通过、planner preflight 全失败。下一版应优先审计 target position、EEF orientation、left-arm workspace、stand layout，还是 planner collision attachment？哪些修改需要新的 impact review？
3. F3 V/H 已完全通过，但 exact return 后瓶子存在 4.10 cm/0.156 的 position/orientation error。请审阅 target actor→EEF transform、release height、support dynamics 与 settle procedure，提出一个不放宽 verifier 的新版本。
4. F4 safe-horizontal waypoint 失败。下一版应优先改变 waypoint construction、planner segmenting，还是需要对 tray layout 做 impact review？不得静默搬设施。
5. GPU guard v2、trace/raw source separation、26-D/N+1、audit metadata 与 failure retention 是否足以作为后续真实 pipeline integration 的基础？
6. 在 F2/F3/F4 修复、F1 三分支和真实 SAPIEN pipeline integration 之前，是否同意继续保持 `BLOCKED_WITH_REASONS`？

## 七、明确禁止误读

- 没有 Stage 0 数据；
- 没有 Stage 1 数据；
- 没有 360 条正式数据；
- 没有模型/VLA/π0.5/compression 训练；
- 没有 F4 strict block reorder；
- 没有完整 F1 三分支成功；
- 没有通过 Temporal Identifiability Gate；
- 当前 probe budget 已执行并耗尽，未使用 planner headroom 不等于 retry 权限。

请基于 repository 中的真实 receipt/trace/code 给出新的 impact review。任何下一轮 GPU 行为都必须先形成新的 implementation version、finite budget 和用户授权。
