# A0 post-setup activity entry-point registry v2

状态：`cpu_audited_current`。机器版本见同名 JSON，registry SHA-256 由其中 payload 自身给出。

## 时间边界

```text
setup_demo
  → move_to_homestate / initial gripper / check_stable / official setup activity
canonical settle
  → 60 × scene.step，仅稳定场景
monitor_start
  → current capture
  → physical anchor capture
  → monitor_stop
cleanup
```

“A0 0 action”只表示 monitor_start 到 monitor_stop 之间：planner query=0、controlled action=0、physics step=0。它不声称 setup_demo 从 scene 创建开始没有动作。

## 固定源码锁

| Source | SHA-256 |
| --- | --- |
| `envs/_base_task.py` | `448f7152b65cb9102217cf5463aa821d72810ca56f63d5a797ec7bd43e23e101` |
| `envs/robot/robot.py` | `3dcd80acc8cab489a4c5edb507cc460dab1724be0226b8d5c4c1b218dee605cb` |
| `envs/robot/planner.py` | `f1012345542483f4cfbac64880a266b7ee0d4a64362d5ec6fd6985ed9c34b564` |
| `envs/camera/camera.py` | `e4d17e99c8a68f44a12bef248a2164f52206efeaf24168172b778cc1e32832dd` |
| `controlled_multi_future/probes/runtime_trace.py` | `37c0a5da686cd08e26c0d737676b771b5a4899a935418eb7052f0f922ca571df` |

官方 tracked commit：`c3ddfa8b97d5519efa828b075999bd0006778e5e`。官方 tracked baseline 未修改。

## 已独立 instrumentation 的类别

- task-level control construction/execution：`delay`、`set_gripper`、双臂 open/close、left/right/together move、`move`、`grasp_actor`、`place_actor`、displacement、direct pose、gripper、back-to-origin、`take_dense_action`、`take_action`；
- robot planner leaves：left/right gripper planner、batch planner、path planner；
- planner wrappers：`_reserve_planner_query`、`set_planner`、`update_world_pcd`；
- direct drive execution：`set_arm_joints`、`Robot.set_gripper`、`move_to_homestate`；
- renderer-only：task `_update_render`、camera `update_picture`；
- physics：`task.scene.step` 使用 instance-local forwarding proxy 独立计数。

所有 wrapper 都是 scene instance 局部安装；不修改官方 class。停止 monitor 或异常 cleanup 时恢复。安装／恢复失败均 fail closed。trace 只作辅助计数源；trace 未初始化不会被解释成“动作数为 0”。

## Receipt 硬 Gate

```yaml
schema_version: cmf_a0_activity_audit_v2
planner_query_delta: 0
planner_query_record_delta: 0
controlled_action_delta: 0
instrumented_control_call_delta: 0
instrumented_planner_wrapper_delta: 0
take_action_count_delta: 0
physics_step_delta: 0
trace_row_delta: 0 | null_when_trace_absent
wrapper_installation_pass: true
wrapper_restoration_pass: true
missing_expected_entry_points: []
```

Renderer updates单独记录并允许非零，不与 physics/action 混称。activity、cleanup 与 `SceneHandle` 的 scene ID／phase 必须一致；每个 sealed activity receipt 只能被 orchestrator 消费一次。
