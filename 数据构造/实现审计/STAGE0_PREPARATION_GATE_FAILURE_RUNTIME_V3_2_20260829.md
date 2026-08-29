# Stage 0 preparation Gate failure — runtime-v3_2

## BLOCKED_WITH_REASONS

Stage 0 要求每个 family 至少有一个完整、同 current、fresh-scene、三分支全部通过的 real root。runtime-v3_2 的结果为：

```yaml
F1_three_of_three: false
F2_three_of_three: false
F3_three_of_three: false
F4_common_and_ABC_ACB_BAC: false
accepted_real_roots: 0
```

因此以下文件被有意保持不存在：

```text
STAGE0_EXECUTION_MANIFEST_V1.md/json
STAGE0_ATTEMPT_BUDGET_V1.md/json
STAGE0_USER_APPROVAL_REQUEST_V1.md/json
```

这不是遗漏，而是 fail-closed Gate 的预期结果。不得通过只选择局部成功分支、放宽 verifier、切换任务语义或降低 3/3 要求来生成这些文件。机器可读证明见同名 JSON。
