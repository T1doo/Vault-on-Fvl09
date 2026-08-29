# F3 shared-prefix diagnosis — runtime-v3_3 v1

状态：`cpu_diagnosis_pass_exact_prefix_gpu_gate_pending`。

runtime-v3_2 三条完整程序的第一个共享 V 均保持 selected-gripper contact fraction=`1.0`，但 EEF negative amplitude 分别为：

| Program | Negative amplitude | 40 mm Gate | Grasp transform |
|---|---:|---|---|
| VHHV | 39.662 mm | fail | stable |
| VHVH | 39.639 mm | fail | unstable before release |
| VVHH | 39.668 mm | fail | stable |

三条均只差约 0.33–0.36 mm，说明这是共享 primitive 问题，不允许按 program 单独调参。

v3.3 统一修复：

```yaml
canonical_prefix: [pregrasp, grasp, close, two_segment_lift, central, shared_first_V]
shared_V_nominal_amplitude_m: 0.055
H_nominal_amplitude_m: 0.05
exact_action_bytes_replayed: true
verifier_threshold_relaxed: false
grasp_boundaries:
  - post_close
  - post_lift
  - post_central
  - post_shared_V
  - before_release
settling_excluded_from_semantic_P: true
program_specific_correction_allowed: false
```

完整 event metrics、速度、contact 与 v3.2 grasp diagnosis 见同名 JSON。新的 exact-prefix real Gate 通过前不能运行完整 F3 root。
