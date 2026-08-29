# Stage 0 preparation Gate failure

## Decision

```text
BLOCKED_WITH_REASONS
```

Stage0准备包的生成前提是F1–F4全部通过完整三分支nonformal root。当前accepted root count=0，四个family均不满足，因此以下文件被明确禁止生成：

```text
STAGE0_EXECUTION_MANIFEST_V1.md/json
STAGE0_ATTEMPT_BUDGET_V1.md/json
STAGE0_USER_APPROVAL_REQUEST_V1.md/json
```

这不是“文件遗漏”，而是fail-closed Gate结果。不得用A0 pass、历史单动作pass、planner preflight或部分task/physical evidence伪造Stage0 root slots、budgets、candidate/prefix hashes或authorization request。

```yaml
a0_pass: true
f1_pass: false
f2_pass: false
f3_pass: false
f4_pass: false
accepted_real_root_count: 0
stage0_package_generated: false
stage0_authorized: false
stage0_trajectory_count: 0
```
