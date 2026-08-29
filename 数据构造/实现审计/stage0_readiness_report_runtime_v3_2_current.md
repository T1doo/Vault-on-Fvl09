# Stage 0 readiness — runtime-v3_2 current

## BLOCKED_WITH_REASONS

A0 已通过，runtime-v3_2 的 F1–F4 有限 nonformal scopes 也全部执行到停止线；但是 accepted real root 仍为 0，Stage 0 不具备用户审批条件。

硬阻塞：

1. F1 blue candidate 在唯一 repair 后仍 planner 失败；
2. F2 inside 物理失败、on/beside 非互斥，而且三条 actual prefix 不同；
3. F3 第一个共享 V realized-motion Gate 失败，VHVH 还有 grasp slip/return failure，三条 prefix 不同；
4. F4 common-X 通过，但 A/B/C right-arm grasp pose 无效，ABC/ACB/BAC 未完整执行；
5. 四个 family 均无 accepted three-branch real root。

```yaml
implementation_version: controlled_multi_future_runtime_v3_2
a0_pass: true
accepted_real_roots: 0
stage0_readiness: blocked_with_reasons
new_gpu_launch_authorized: false
stage0_authorized: false
stage0_trajectory_count: 0
stage1_trajectory_count: 0
formal_f1_f4_trajectory_count: 0
h_reveal: null
```

`STAGE0_EXECUTION_MANIFEST_V1`、`STAGE0_ATTEMPT_BUDGET_V1` 和 `STAGE0_USER_APPROVAL_REQUEST_V1` 均因 Gate 失败而明确不生成。机器可读 current 状态见同名 JSON。
