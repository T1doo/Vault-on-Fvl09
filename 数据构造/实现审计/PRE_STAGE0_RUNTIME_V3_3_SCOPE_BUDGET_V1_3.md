# runtime-v3_3 pre-Stage-0 scope budget v1.3

本addendum依据用户“预算不限、允许持续找原因并修正”的明确授权，只新增F2/F3/F4 revision-4的source-distinct one-shot资格。它仍不允许automatic retry、recovery、覆盖失败、Stage 0、正式采集或训练。

| Scope | Planner hard limit | Source-bound envelope | Execution limit | Timeout |
|---|---:|---:|---:|---:|
| F1 root | 64 | 46 | 3 | 5400 s |
| F2 root | 96 | 32 | 4 | 7200 s |
| F3 root | 160 | 96 | 4 | 10800 s |
| F4 staged + root | 256 | 116 | 10 | 20400 s |

F2=`19 prefix + 3 inside + 4 on + 6 beside = 32`。F3 r4保持相同物理动作，仅增加证据保存，仍=`21 prefix + 75 suffix = 96`。F4仍=`44 staged + 72 full = 116`。所有recovery=0，每revision最多一次full-root invocation；失败或early-stop均消费且永久保留。

```yaml
design_version: controlled_multi_future_f1_f4_v1_2
implementation_version: controlled_multi_future_runtime_v3_3
implementation_revision: runtime_v3_3_revision4_impact_addendum_v1
maximum_new_implementation_revisions_per_family: 4
maximum_full_root_execution_per_revision: 1
allowed_physical_gpu_indices: [0,1,2,3,4,5,6,7]
automatic_retry: false
recovery_attempts: 0
stage0_authorized: false
```

