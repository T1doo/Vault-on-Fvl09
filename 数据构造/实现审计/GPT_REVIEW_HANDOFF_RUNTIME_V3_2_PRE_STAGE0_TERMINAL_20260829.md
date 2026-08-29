# 给 GPT 的 runtime-v3_2 审阅交接

请锁定并审阅 Vault `main`。完整 terminal GPU evidence 基线 commit 是：

```text
cabdb51d865d9407c6b4c594b37da7a3f94bf7f5
```

包含本 handoff、current registry/readiness 与总方案更新的 closure content commit：

```text
58e932cb236df96efc3444ba22cb9d6882d7c27a
```

## 建议优先阅读

1. `数据构造/实现审计/COMPLETE_PRE_STAGE0_RUNTIME_V3_2_EXECUTION_REPORT_20260829.md/json`
2. `数据构造/实现审计/stage0_readiness_report_runtime_v3_2_current.md/json`
3. `数据构造/实现审计/f1_f4_implementation_registry_v3_2_current.md/json`
4. `数据构造/实现审计/STAGE0_PREPARATION_GATE_FAILURE_RUNTIME_V3_2_20260829.md/json`
5. `数据构造/实现审计/runtime_v3_2_terminal_static_audit_20260829.json`
6. `数据构造/实现审计/RUNTIME_V3_2_TERMINAL_PUBLICATION_RECEIPT_20260829.json`
7. `数据构造/正式数据构造日志.md` 第 103–122 节
8. `数据构造/实现审计/F2_OFFICIAL_ASSET_COMPATIBILITY_MATRIX_V2.md/json`
9. `数据构造/实现审计/F4_ARM_ASSET_LAYOUT_IMPACT_REVIEW_V6.md/json`

## 本轮完成内容

- 公共 planner dtype、raw timing、partial trace、authorization/guard 与 append-only root evidence 加固；
- F1 公平三分支 planner 覆盖；
- F2 官方 can/box 全资产兼容矩阵及同 object/arm 三关系真实 rollout；
- F3 post-grasp diagnosis 与 VVHH/VHVH/VHHV 完整真实 raw；
- F4 right-arm layout、common-X 完整成功证据及完整程序 preflight 尝试；
- active / byte-equal snapshot 各 187/187 tests passed；
- 所有获准 nonformal GPU scopes 到达有限停止线，未无限重试。

## 当前裁决

```text
BLOCKED_WITH_REASONS
```

accepted real root=0，因此明确不批准 Stage 0。请重点审阅：

1. F1 blue lift 是否需要新的 scene/pose impact review；
2. F2 box2 inside target、facility layout 与互斥 predicate 是否需要新版本；
3. strict executed-prefix 是否应改为预生成/重放完全相同 action bytes，而不是依赖 fresh planner 自然复现；
4. F3 shared-first-V amplitude与 VHVH grasp slip 的修复方向；
5. F4 right-arm project block grasp-pose 为何返回标量无效值，以及是否允许在下一实现版本修复。

请不要把 F2 beside、F3 局部完整程序或 F4 common-X 的成功升级为 family/root/Stage0 ready。当前没有 Stage0/Stage1/formal data、训练、`H_reveal`、compression 或 π0.5。
