# controlled_multi_future_runtime_v3_1 implementation proposal

状态：`cpu_static_implemented_pending_gpt_review`。

```yaml
design_version: controlled_multi_future_f1_f4_v1_2
implementation_version: controlled_multi_future_runtime_v3_1
root_orchestrator: real_sapien_pilot_root_orchestrator_v1_1
current_hash: current_context_hash_v2
physical_anchor: physical_anchor_v2
raw_schema: cmf_raw_attempt_v2_1_1
primary_action_layout: controller_effective_setpoint_v1_layout_v2_1
gpu_probe_authorized: false
stage0_authorized: false
formal_data: false
stage0_data: false
```

## 本轮实现

- task/physical feasibility 与 planner solvability 分账；candidate universe 在前者通过后 freeze 一次；
- 每场 scene 使用唯一 `scene_instance_id` 与绑定 cleanup receipt，cleanup/orphan 不确定立即停止；
- planned spec、program、planner variant 在每次 adapter call 前后做 hash 不可变性检查；
- feasibility 前保存 provisional programs/task trees/prefix；
- finalizer 独立重查 branch current、anchor 和实际 executed-prefix bytes/steps/start/end anchor；
- raw 写入后、verifier 前先保存 manifest 与 branch partial receipt；
- raw 增加真实 scene timestep、planner query ID/active interval/source 和 NPZ/manifest/trace integrity hashes；
- current hash 分离 model-visible 与 hidden physical components，实际 camera config 与实体 schema 均强制；
- physical anchor 使用 sign-invariant quaternion angular error，并保存 actor velocity/sleep state、drive targets 与 physics config；
- 实现 lazy-import concrete RoboTwin adapter、F1 root runner、F2/F3/F4 repair runner、A0 zero-action entry point 与内容哈希授权 receipt Gate。

## Family 当前边界

| Family | 当前 runner scope | 完整 root 状态 |
| --- | --- | --- |
| F1 | red/green/blue 三分支、实际相同 prefix、3/3 root | 已静态实现，未运行 |
| F2 | 固定同 can/left/stand；六个 fresh-scene planner variants；chained preplace→release；beside execution | 已静态实现，未运行 |
| F3 | V→H realized diagnosis、grasp-transform drift、release samples、return | 完整 VVHH/VHVH/VHHV 明确未运行，root verifier fail-closed |
| F4 | common-X Route1/Route2 fresh-scene repair、combined object/gripper carry envelope | A/B/C 与 ABC/ACB/BAC 明确未运行，root verifier fail-closed |

CPU current：active/snapshot 70/70 tests passed，57 Python files compile passed；root-cpu4 synthetic dry-run accepted。它们不证明真实 SAPIEN。

任何 GPU 运行仍必须先经 GPT/user 审阅并生成独立、内容哈希的授权 receipt。Stage 0 明确禁止。
