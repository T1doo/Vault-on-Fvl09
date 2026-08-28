# controlled_multi_future_runtime_v3 implementation proposal

状态：`cpu_static_implemented_proposed_for_user_review`。

```yaml
design_version: controlled_multi_future_f1_f4_v1_2
implementation_version: controlled_multi_future_runtime_v3
raw_layout_version: controller_effective_setpoint_v1_layout_v2_1
gpu_probe_authorized: false
stage0_authorized: false
formal_data: false
stage0_data: false
```

科学设计、分母、split 和 F3/F4 programs 均未变化。

| Family | 新版本 | CPU/static 合同 | 当前状态 |
| --- | --- | --- | --- |
| F1 | `f1_three_branch_coverage_v3` | red→green→blue 参数化；shared target-neutral canonical prefix；每分支 fresh scene；同 scene/current/prefix hashes；仅 3/3 pass | implemented, not run |
| F2 | `f2_workspace_reachability_v4` | 固定 6 个 complete pose candidates；同 planner seed/start state；preplace+release planner；无换臂/换物体 fallback | implemented, not run |
| F3 | `f3_release_dynamics_diagnosis_v3` | before-release 与 1/5/10/25/50/125/250/after-rest diagnostics；pad footprint/contact normal/impulse/actual gripper qpos；条件式 correction Gate | implemented, not run |
| F4 | `f4_segmented_common_carry_v3` | obstacle-derived minimum height；Route 1/2 固定顺序；每段 endpoint preflight；tray pose 禁止变化 | implemented, not run |

新增 `RealSapienPilotRootOrchestratorV1`：先捕获 pristine current/anchor，再用三个 disposable scenes 做 feasibility；全部通过后 candidate/task-tree/prefix 只 freeze 一次；三个 rollout 各自 fresh scene；root finalizer 必须 3/3 receipts。

Raw v2_1 明确保存 N+1 state timestamps、N action start/end timestamps、`planner_goal_eef_pose`、drive-target readback 和实际左右 gripper joint qpos。Current hash 现在强制包含左右 wrist、actual gripper state 和 camera config/version。

CPU current：45/45 tests passed；cpu5 raw dry-run 与 root-cpu2 dry-run passed。它们仍是 synthetic evidence，不证明真实 SAPIEN。

任何 GPU 运行都必须先审阅并批准新的 budget。Stage 0 仍明确禁止。
