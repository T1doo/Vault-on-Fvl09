# 用户授权：runtime-v3_3 continued versioned repairs

2026-08-30，用户在当前 Codex 线程明确说明：

> 预算是无限的，你找出原因不断修正是可以接受的。

本项目将该授权落实为“可以持续新增有证据依据的 source-distinct implementation revisions”，而不是无限自动 planner retry：

- 当前 addendum 先将 F2/F3/F4 的 implementation revision 上限从 2 增加到 3；
- 每个 family 的 revision-3 仍最多一次完整 root invocation；
- 每次运行仍有有限 planner、execution、timeout，recovery=0，automatic retry=false；
- 每次失败、早停、cleanup 和 GPU receipt 永久保留；
- 后续若仍需 revision-4+，可以依据本次用户授权继续形成新的 versioned impact addendum，但不得复用或覆盖旧 authorization/ledger/output；
- physical GPU0–7 中任一 independently fresh-idle 卡可使用，独立 family 可在不同卡并行；
- 本授权不批准 Stage 0、Stage 1、360 条正式数据、训练、compression 或 π0.5；
- 不允许改变 F1–F4 科学问题、F3/F4 程序、同一对象/执行臂约束或通过放宽 verifier 获得成功。

```yaml
design_version: controlled_multi_future_f1_f4_v1_2
implementation_version: controlled_multi_future_runtime_v3_3
approved: true
maximum_new_implementation_revisions_per_family: 3
maximum_full_root_execution_per_revision: 1
automatic_retry: false
recovery_attempts: 0
allowed_physical_gpu_indices: [0, 1, 2, 3, 4, 5, 6, 7]
parallel_independent_jobs: true
formal_stage0_authorized: false
stage1_authorized: false
formal_collection_authorized: false
training_authorized: false
```
