# GPT 审阅入口：F1–F4 runtime-v3 CPU/static 前置实现

## 如何定位

- GitHub repository：`https://github.com/T1doo/Vault-on-Fvl09`
- Branch：`main`
- 本轮 content commit：`dec39d65ce1607740cef311ca5a4b66572c12ce7`
- 科学设计：`controlled_multi_future_f1_f4_v1_2`
- 实现版本：`controlled_multi_future_runtime_v3`
- Raw layout：`controller_effective_setpoint_v1_layout_v2_1`
- 当前裁决：`BLOCKED_WITH_REASONS`
- `gpu_probe_authorized=false`
- `stage0_authorized=false`

请先读本文件，再按下述顺序核对机器证据。本轮是在上一份 GPT review 基础上完成的 **CPU/static implementation repair**；没有运行 runtime-v3 GPU probe，也没有实现或验证真实 SAPIEN adapter，因此不能把 45/45 tests 或 synthetic dry-run 解读为 Stage 0 ready。

## 一、建议阅读顺序

1. `Idea/项目核心Idea.md`
2. `数据构造/数据构造方案.md`
3. `数据构造/实现审计/runtime_v2_bounded_probe_execution_report_20260828.md`
4. `数据构造/实现审计/controlled_multi_future_runtime_v3_implementation_proposal.md`
5. `数据构造/实现审计/pilot_attempt_budget_runtime_v3_proposal.md`
6. `数据构造/实现审计/f1_f4_implementation_registry_v3_cpu_current.md`
7. `数据构造/实现审计/stage0_readiness_report_runtime_v3_current.md`
8. `数据构造/实现审计/runtime_v3_cpu_static_audit_20260828.json`
9. `数据构造/正式数据构造日志.md` 的 §41–§47

Proposal、budget、registry 和 readiness 均有同名机器可读 `.json`。代码审阅快照位于：

```text
数据构造/实现审计/代码审阅快照/
```

## 二、上一轮真实物理证据仍如何解释

Runtime-v2 immutable receipts/traces 保留不覆盖：

| Family | runtime-v2 真实 SAPIEN 终态 | 当前 claim boundary |
| --- | --- | --- |
| F1 | 红方块分支通过 | 仅证明红分支 `true-inside + stable + continuous box body-pair contact + non-target stable + rest`；没有接触法向证据，不能升级为严格盒底支撑；绿/蓝未运行 |
| F2 | 三个预注册 stand yaw 的 planner preflight 全失败 | 同一 `071_can/base1 + left arm + 074_displaystand/base3` 尚未完成 beside |
| F3 | realized V/H、指定夹爪连续性通过；return-equivalence 失败 | position/orientation error 约 `0.04096 m / 0.15587`，尚不能称完整 F3 |
| F4 | common-X 的 `safe_horizontal_waypoint` planner 失败 | A/B/C 与 ABC/ACB/BAC 未运行 |

这些历史真实 runs 全部是 `formal_data=false`、`stage0_data=false`。本轮没有新增任何真实物理结果。

## 三、这轮根据 GPT review 完成的代码修复

### 1. Raw layout v2_1

`controlled_multi_future/raw_writer.py` 与 `controlled_multi_future/probes/runtime_trace.py` 现在明确区分：

- `state_timestamps`：`N+1`；
- `action_interval_start_timestamps`：`N`，严格等于 `state_timestamps[:-1]`；
- `action_interval_end_timestamps`：`N`，严格等于 `state_timestamps[1:]`；
- `planner_goal_eef_pose`：planner 的双臂 EEF goal，不再误称 per-step planner trajectory；
- `gripper_drive_target_readback`：drive target readback，不再误称真实 aperture；
- `realized_left_gripper_joint_qpos` 与 `realized_right_gripper_joint_qpos`：实际关节位置审计流；
- primary action stream 仍是 `controller_effective_setpoint_v1`、250 Hz、26-D，并强制 `N actions / N+1 states`。

### 2. Same-current hash

`controlled_multi_future/current_hasher.py` 现在强制包含：

- head RGB；
- left/right wrist RGB；
- robot state；
- actual gripper state；
- object instance/pose/role/layout；
- camera config/version；
- scene seed 与 generator version。

### 3. F1–F4 runtime-v3 contracts

新增 `controlled_multi_future/runtime_v3_contracts.py`：

- F1 `f1_three_branch_coverage_v3`：`red → green → blue` 固定顺序、target-role 参数化、target-neutral common prefix、每分支 fresh scene、同 scene/current/prefix hash，仅 3/3 通过；
- F2 `f2_workspace_reachability_v4`：最多六个预注册 complete pose candidates、固定顺序、相同 planner seed/start state、同时检查 release/pre-place planner、joint margin、carried swept geometry 和设施距离；禁止换臂、换罐头或无限加 yaw；
- F3 `f3_release_dynamics_diagnosis_v3`：记录 before-release、release 后 1/5/10/25/50/125/250 帧和 after-rest；区分释放前 offset 与释放后 dynamics；只有前者可解锁一次确定性 correction，禁止放宽 verifier；
- F4 `f4_segmented_common_carry_v3`：按资产障碍高度计算最低安全高度，固定 Route 1/Route 2 顺序，每段 endpoint preflight，禁止静默移动 tray。

这些是 fail-closed contracts 和 CPU logic，不是四个 family 的真实 SAPIEN rollout 实现成功证据。

### 4. Root-level orchestrator

新增 `controlled_multi_future/root_orchestrator.py`：

```text
pristine scene capture current/anchor
→ close
→ three disposable fresh feasibility scenes
→ freeze candidate/task-tree/prefix exactly once
→ three fresh rollout scenes
→ retain all branch receipts
→ require 3/3 in root finalizer
```

`RealSapienPilotRootOrchestratorV1` 的 orchestration contract 与 abstract adapter 已实现；`real_sapien_adapter=unimplemented`，当前仅由 synthetic adapter 覆盖。

## 四、当前 CPU evidence

### Raw v2_1 current dry-run

```text
数据构造/实现审计/probe_outputs/
  nonformal_pipeline_dry_run_runtime_v3_raw_v2_1_20260828_cpu5/
```

- receipt SHA-256：`d1018661f1503c653c64bace7edd11772e85df6455ec02d50320d9107a7c6ba7`
- manifest SHA-256：`acada9425cd877295d5113221cd9eb6d186d53fe5f6c69fd1ed1d74d73404b13`
- raw NPZ SHA-256：`d56b902addcaa3f367f78b581efaefa0d8807519a992829fa84ed315230e2785`
- schema：`cmf_raw_attempt_v2_1`
- `formal_data=false`、`stage0_data=false`、`synthetic=true`

`cpu3` 暴露旧 manifest schema，`cpu4` 位于 current-hash 最终强化前；两者作为 superseded failure/iteration evidence 保留，`cpu5` 才是 current raw evidence。

### Root orchestrator current dry-run

```text
数据构造/实现审计/probe_outputs/
  nonformal_root_pipeline_dry_run_runtime_v3_20260828_cpu2/
```

- root receipt SHA-256：`ff9645657f271bb4683c04ea15cc50cc173e5b5528db45e4273ba0df9a7e432e`
- candidate frozen spec SHA-256：`bedff43fd43e04e314e92eed67ab3dc78393127b89dd25dc5584137aefe596f5`
- pristine current/anchor 在 feasibility 前捕获；
- disposable feasibility receipts：3；
- `freeze_call_count=1`；
- fresh branch receipts：3；
- synthetic root finalizer：3/3 accepted；
- `formal_data=false`、`stage0_data=false`、`synthetic=true`。

`root-cpu1` 位于 current-hash 最终强化前，作为 superseded evidence 保留；`root-cpu2` 是 current root evidence。

## 五、测试与源码边界

- Active RoboTwin source：`/nfs_share/lijunhui/Robotwin2/project/RoboTwin/controlled_multi_future/`
- Official tracked baseline commit：`c3ddfa8b97d5519efa828b075999bd0006778e5e`
- Official tracked baseline modified：`false`
- Active tests：45/45 passed
- Vault byte-equal snapshot tests：45/45 passed
- Python compile：43 files passed
- Active source 与 Vault snapshot：byte-equal
- `__pycache__/.pyc`：无

重点审阅：

```text
数据构造/实现审计/代码审阅快照/controlled_multi_future/
  current_hasher.py
  raw_writer.py
  runtime_v3_contracts.py
  root_orchestrator.py
  probes/runtime_trace.py
  probes/pipeline_dry_run.py
  probes/root_pipeline_dry_run.py

数据构造/实现审计/代码审阅快照/tests/controlled_multi_future/
  test_pipeline_contracts.py
  test_runtime_v3_contracts.py
  test_root_orchestrator.py
```

## 六、尚未完成的真实实现与 blocker

1. `RealSapienPilotRootAdapterV1` 的真实 SAPIEN scene/family adapter 尚未实现；
2. F1 red/green/blue 3/3 尚未运行；
3. F2 六个 complete pose candidates 的资产坐标与高度数值尚未接到真实 scene 并运行；
4. F3 pad footprint、contact normal/impulse、release timepoints 尚未接到真实 trace 并运行；
5. F4 obstacle-top、segmented route 和 carry-neutral 尚未接到真实 planner 并运行；
6. real SAPIEN root integration 尚未运行；
7. runtime-v3 finite budget 尚未获批、未冻结；
8. Stage 0 仍未授权。

因此当前裁决必须保持：

```text
BLOCKED_WITH_REASONS
```

## 七、待 GPT 审阅的 finite budget（仅 proposal）

| Family | execution 上限 | planner query 上限 | timeout | terminal stop |
| --- | ---: | ---: | ---: | --- |
| F1 | 3，red/green/blue 各 1 | 12 / branch | 1200 s / branch | 低于 3/3 则 F1 incomplete；非 cleanup failure 时仍执行全部预注册分支 |
| F2 | 最多 1 | 16 total，最多 6 candidates | 1200 s | 全失败进入 `f2_stand_layout_impact_review_v5` |
| F3 | 1 次 diagnosis；仅前置 offset 被证明时再 1 次 correction | 16 / run | 1800 s / run | post-release dynamics 直接进入 physics impact review |
| F4 | 固定顺序最多 2 routes，各 1 次 | 16 / route | 1800 s / route | 两 route 全失败进入 `f4_tray_layout_impact_review_v4` |

机器状态保持：

```yaml
status: proposed_for_user_review
approved: false
frozen: false
gpu_probe_authorized: false
```

当前 workspace GPU policy 是 physical fvl05 GPU0–7 中任一 independently fresh-idle 卡，但该一般设备规则本身不构成 runtime-v3 probe 授权。

## 八、希望 GPT 重点裁决

请不要批准 Stage 0；请先完成以下 code/evidence review：

1. Raw v2_1 的 action/state interval、planner-goal 命名、drive-target readback 与 actual gripper qpos 是否消除了上一轮指出的语义歧义？
2. `CurrentContextHasher` 的输入是否足以作为 same-current 最低合同；真实 SAPIEN adapter 还必须补哪些 camera/object/physics 字段？
3. F1–F4 contracts 是否忠实实现上一轮建议，尤其是 F1 无 success-only selection、F2 candidate fairness、F3 条件式诊断、F4 route terminal stop？
4. Root orchestrator 的 pristine-current-before-feasibility、freeze-once、three-fresh-rollouts、3/3 finalizer 顺序是否正确？接口中是否仍存在真实 adapter 可绕过的状态污染路径？
5. 上述 proposed finite budget 是否可以批准为下一轮 **bounded nonformal GPU probe**，或还需先改哪些 CPU/code 项？即使批准，也不得视为 Stage 0 authorization。
6. 在真实 family adapters、四个 repair probes 与一个真实 SAPIEN root integration 完成前，是否同意继续保持 `BLOCKED_WITH_REASONS`？

## 九、明确禁止误读

- 没有 runtime-v3 GPU execution；
- 没有 Stage 0 数据；
- 没有 Stage 1 数据；
- 没有 360 条正式数据；
- 没有训练机制模型、VLA、π0.5 或 compression；
- 没有 F1 三分支真实 3/3；
- 没有 F2/F3/F4 完整成功；
- 没有真实 SAPIEN root-level integration；
- 没有 Temporal Identifiability、`H_reveal`、compression 或 policy-transfer 结论。

请基于 proposal、registry、机器 receipts、代码快照和测试给出审阅；若建议下一轮 GPU 运行，请把它明确写成新的有限非正式授权建议，而不是 Stage 0 approval。
