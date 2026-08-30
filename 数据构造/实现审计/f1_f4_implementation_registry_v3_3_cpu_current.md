# F1–F4 implementation registry：runtime-v3_3 revision-6 CPU current

```yaml
design_version: controlled_multi_future_f1_f4_v1_2
implementation_revision: runtime_v3_3_revision6_impact_addendum_v1
accepted_nonformal_roots: 1/4
stage0_authorized: false
```

| Family | revision-6实现 | Envelope | 状态 |
|---|---|---:|---|
| F1 | 无变化；revision-2 3/3 accepted | 46/3/0 historical | `accepted_nonformal_root` |
| F2 | inside 10 warmup + final50原阈值；full60安全与final geometry | 32/3/0 | `r6_cpu_ready_not_run` |
| F3 | target-quaternion-specific fl6/7/8 projection + live model/support/link compound clearance | 96/3/0 | `r6_cpu_ready_not_run` |
| F4 | A/B/C统一top-down pregrasp+grasp z+16mm；A micro+20mm | 13/1/0 | `r6_micro_cpu_ready_not_run` |

Active/snapshot均359/359，diff零；source=`3b771f97a5b2b53db53bf71ec9f1fe15727614a1303e2f415197e65655580a7d`，budget=`9f0fb00bf7a9d1c4317be2233e53f18ee670c65b29eb08e56c7d7a5c3b9930cb`。三family P0审计通过；F2-r6、F3-r6、F4-r6 A-only micro 的精确 single-use bundles 已发布但尚未消费，r6 GPU尚未运行。
