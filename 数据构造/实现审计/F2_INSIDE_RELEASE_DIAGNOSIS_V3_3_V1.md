# F2 inside release diagnosis — runtime-v3_3 v1

基于 runtime-v3_2 final inside branch 的 immutable raw 复核，分类为：

```text
box_wall_collision_and_ejection_before_gripper_release
```

关键事实：

- preplace 结束时 can 仍与指定左夹爪接触；
- release descent 中 state 2252 首次失去指定夹爪接触；
- state 2268 can center 已离开桌面范围；
- 真正开夹爪前，can 已位于约 `[-0.584, -0.206, 1.626] m`、速度约 `3.02 m/s`，且完全不在 cavity 内；
- 因此失败不是释放后滚动，也不是 retreat 才带出，而是下降进盒过程中撞壁并高速弹出。

选定的单一全局修复：

```yaml
inside_suffix:
  actor_to_eef_target: frozen
  staged_world_z_descent_offsets_m: [0.10, 0.06, 0.03, 0.00]
  intermediate_gates: [full_OBB, can_box_contact, selected_gripper_contact]
  retreat: reverse_same_world_z_stages
layout_version: f2_box2_mutually_exclusive_facilities_v2
full_OBB_verifier_relaxed: false
automatic_retry: false
```

before-release、after 1/5/10/25/50/125/250、after-retreat、after-rest 的 pose/velocity/OBB/contact/EEF/gripper/table-clearance 全量记录见同名 JSON。
