# F1–F4 implementation registry：runtime-v3_3 revision-6 terminal current

```yaml
design_version: controlled_multi_future_f1_f4_v1_2
implementation_revision: runtime_v3_3_revision6_impact_addendum_v1
accepted_nonformal_roots: 1/4
stage0_authorized: false
new_gpu_launch_authorized: false
```

| Family | revision-6真实结果 | 计数 planner/execution/recovery | 下一source-distinct修复 |
|---|---|---:|---|
| F1 | revision-2 3/3 accepted，未重跑 | 46/3/0 historical | 无 |
| F2 | `on`、`beside` accepted；`inside`在开夹后卡于盒外 | 32/3/0 | 固定证据驱动的inside-only tracking compensation |
| F3 | canonical prefix通过；三个program在suffix planner前触发旧键`KeyError` | 21/0/0 | projection consumer接线、partial evidence与异常分类 |
| F4 | +16 mm解决碰桌，A实际微抬17.3066 mm；旧verifier读错actor且把零冲量pair当接触 | 13/1/0 | role-A stream + nonzero-impulse接触语义后fresh A-only micro |

F4结束时外部非本任务进程占用GPU0，Guard按设计保持`failed_cleanup_uncertain`；task-owned orphan=0，但本轮不会改写Guard终态或retroactive accept。完整机器审计见`F2_F3_F4_RUNTIME_V3_3_REVISION6_TERMINAL_AUDIT_AND_R7_IMPACT_REVIEW_20260830.*`。
