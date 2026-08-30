# F1–F4 implementation registry：runtime-v3_3 revision-5 terminal current

```yaml
design_version: controlled_multi_future_f1_f4_v1_2
implementation_version: controlled_multi_future_runtime_v3_3
accepted_nonformal_roots: 1/4
stage0_authorized: false
```

| Family | revision-5真实结果 | 下一source-distinct修复 | 状态 |
|---|---|---|---|
| F1 | revision-2 red/green/blue 3/3 accepted，未重跑 | 无 | `accepted_nonformal_root` |
| F2 | planner32/execution3；on、beside accepted；inside仅一次early angular settle spike失败 | +10 no-command warmup，原final50阈值与完整60安全Gate | `r5_incomplete_r6_cpu_in_progress` |
| F3 | planner96/execution3；三程序一致在pre-open geometry clearance失败，其他checks通过 | center-aware bottle+assembly 10mm真实净空 | `r5_incomplete_r6_cpu_in_progress` |
| F4 | repaired prefix/pregrasp/noninterference通过；grasp双指碰桌，close前终止 | A/B/C统一top-down pregrasp+grasp world-z +16mm，micro仍+20mm | `r5_micro_failed_r6_cpu_in_progress` |

R5 source SHA=`0d19e5d0ace6f3115c686a77485f72b12858023e18dd0cab3fc49f610aa0b33b`；三个Guard均cleanup/GPU release/source-lock通过。Evidence trees：F2=`98e6ea3f…d911a1`，F3=`94299900…bf3e0`，F4=`93228220…8dcf8`。

Stage0/1/formal/training仍为0/未授权。Revision-6必须重新完成CPU tests、byte-equal snapshot、publication和exact-scope authorization。
