# runtime-v3_3 pre-Stage-0 scope budget v1.2

状态：`user_authorized_pre_stage0_nonformal_v3_3_revision3_impact_addendum`

用户于 2026-08-30 明确允许在完整保存失败证据的前提下继续 versioned implementation repairs。本预算只新增 F2/F3/F4 revision-3 的单次执行资格；它不授权自动重试、recovery、Stage 0、正式采集或训练。若 revision-3 仍失败，后续代码修复仍须形成新的 source-distinct version、机器 impact review 和新的单次授权包。

每个 revision 最多一次 full-root invocation；每次 Guard 启动即原子消费，不因 planner early-stop、branch execution=0 或语义失败而退还。GPU0–7 任一 independently fresh-idle 卡可用，独立 family 可在不同卡并行。

| Scope | Planner limit | Source-bound envelope | Execution limit | Timeout |
|---|---:|---:|---:|---:|
| F1 root | 64 | 46 | 3 | 5400 s |
| F2 root | 96 | 68 | 4 | 7200 s |
| F3 root | 160 | 96 | 4 | 10800 s |
| F4 staged + root | 256 | 116 | 10 | 20400 s |

F2 envelope=`19 prefix + 3 inside + 4 on + 6×7 beside = 68`。F3 envelope=`21 prefix + 3×25 suffix = 96`。F4 envelope=`44 staged + 72 full root = 116`。全部 recovery=0，automatic retry=false。

```yaml
design_version: controlled_multi_future_f1_f4_v1_2
implementation_version: controlled_multi_future_runtime_v3_3
maximum_new_implementation_revisions_per_family: 3
maximum_full_root_execution_per_revision: 1
formal_data: false
stage0_data: false
stage0_authorized: false
```

