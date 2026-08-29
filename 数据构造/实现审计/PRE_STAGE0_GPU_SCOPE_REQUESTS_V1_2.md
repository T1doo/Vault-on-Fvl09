# Pre-Stage-0 GPU Scope Requests V1.2

```yaml
status: A0_passed_family_scopes_require_separate_review
implementation_revision: runtime_v3_1_cpu_hardening_v5_1_postmortem_validation
formal_data: false
stage0_data: false
stage0_authorized: false
new_gpu_launch_authorized: false
```

本包 supersede V1.1 作为 current request状态入口，但不修改V1/V1.1或run1/run2历史证据。

新A0-only request：

```text
scope_requests/runtime_v3_1_postmortem_validation_a0_v1/
A0_F1_seed20260829_run3_postmortem_validation.request.json
```

该request已通过全新source lock和one-shot authorization执行并消费；结果为`passed_nonformal_A0`。它不可重放，也不授权family scopes。

当前硬边界：

- F1/F2/F3/F4 action probes未执行；
- real-root integration未执行；
- 旧V1/V1.1 family request绑定旧source/precondition，当前不可launch；
- 下一轮family scopes必须重新审阅source、预算、命令、namespace并签发各自one-shot authorization；
- Stage 0仍禁止。
