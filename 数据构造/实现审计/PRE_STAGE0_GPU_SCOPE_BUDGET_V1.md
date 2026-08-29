# Pre-Stage-0 非正式 GPU Scope Budget V1

```yaml
schema_version: cmf_runtime_v3_1_scope_budget_v1_2
implementation_revision: runtime_v3_1_cpu_hardening_v5_1
status: user_authorized_pre_stage0_nonformal
approved: true
frozen: true
gpu_probe_authorized: true
stage0_authorized: false
formal_data: false
stage0_data: false
```

本预算仅执行用户在 `USER_AUTHORIZATION_COMPLETE_PRE_STAGE0_WORK_20260829.md/json` 中批准的 Stage 0 前非正式验证。每次真实运行仍需独立 scope request、launch-time source lock、有效期不超过一小时的 one-shot authorization、atomic GPU guard、唯一 output namespace 与 consumption receipt。

| Scope | 有限 envelope | 自动重试 |
|---|---|---:|
| A0 | 1 pristine + 3 fresh；post-setup planner/control/physics 均为 0；600 秒 | 否 |
| F1 | red/green/blue 各执行 1 次；每 branch 最多 12 planner queries、1200 秒 | 否 |
| F2 | 最多 6 个 workspace candidates、16 preflight queries、最多 1 次 repair execution；完整 inside/on/beside 各 1 次 | 否 |
| F3 | 1 次 diagnosis；严格条件满足时 1 次 repair；VVHH/VHVH/VHHV 各 1 次 | 否 |
| F4 | Route1/Route2 各最多 1 次；其后 A/B/C、noninterference 与 ABC/ACB/BAC 均为固定一次 | 否 |
| Real root integration | F1 三分支 fresh-scene root integration，各 1 次 | 否 |

共同停止线：cleanup/orphan/GPU release 不确定立即停止；不得无限试 pose、换 object、分支换 arm、删除失败证据或放宽 verifier。每个 family 最多两个新的 implementation repair revisions。

机器可读唯一细节见 `PRE_STAGE0_GPU_SCOPE_BUDGET_V1.json`。本文件不授权 Stage 0、Stage 1、正式数据、训练、compression 或 π0.5。
