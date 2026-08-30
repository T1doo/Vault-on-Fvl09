# F1–F4 implementation registry：runtime-v3_3 revision-7 CPU current

```yaml
design_version: controlled_multi_future_f1_f4_v1_2
implementation_revision: runtime_v3_3_revision7_impact_addendum_v1
accepted_nonformal_roots: 1/4
stage0_authorized: false
new_gpu_launch_authorized: true
```

| Family | revision-7实现 | Envelope | 状态 |
|---|---|---:|---|
| F1 | 无变化；revision-2 3/3 accepted | 46/3/0 historical | `accepted_nonformal_root` |
| F2 | r6-evidence固定SE(3) compensation仅替换inside target0；alignment只诊断 | 32/3/0 | `r7_cpu_ready_not_run` |
| F3 | 修正确projection key；planner前boundary/partial trace；implementation-error分账 | 96/3/0 | `r7_cpu_ready_not_run` |
| F4 | 强制role-A pose；零冲量pair只audit，物理接触仍用既有`>1e-10` | 13/1/0 | `r7_micro_cpu_ready_not_run` |

Active/snapshot均382/382、diff零；source=`2ed82e7a5e6a2a03a3cf7b1cfb3dde82acba637f24c574c64c47099516ee72c8`，budget=`1a3e2e18acc8af984dbb76e637ac140c930c332748202e7b61564b77c86f8d62`。三family P0审计通过；三份r7 exact single-use bundles已发布但尚未消费，GPU output不存在。
