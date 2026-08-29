# Stage 0 readiness：runtime-v3_3 CPU current

## BLOCKED_WITH_REASONS

CPU/static基线和真实canonical-prefix smoke已经通过。F4首次no-action IK三角色均在旧layout pregrasp失败，现已形成统一right-workspace layout v3 CPU修复；在real IK复验和F1–F4完整roots前仍不能启动Stage 0。

已经具备的部分：

- canonical prefix单次生成与三fresh exact replay代码；
- frozen suffix planner/execution接口；
- current/anchor、raw、verifier、cleanup与3/3 root finalizer；
- F1公平planner evidence、F2动态inside与互斥layout、F3 shared-V物理Gate、F4 no-action IK与staged blocks；
- 与冻结JSON一致的有限预算及one-shot/revision/GPU guard链；
- active和byte-equal snapshot各`245/245 tests passed`。

仍缺的真实证据：

```text
F4 A/B/C no-action right-arm IK
F1 accepted root
F2 accepted root
F3 accepted root
F4 staged A/B/C/AB Gate + accepted root
```

当前计数：Stage 0=0、Stage 1=0、formal F1–F4=0；没有训练、H-reveal、compression或π0.5。

下一步只能先发布CPU baseline v1.2，再按fresh source lock和≤1h one-shot authorization逐scope执行有限nonformal验证。四个family全部accepted以前，不生成Stage 0 manifest/budget/request。

补充：prefix-smoke run1/run2均在GPU0 busy时保持未消费，随后两轮source hardening使其source lock失效，现均明确superseded。任何真实launch必须使用v1.2 baseline之后生成的全新run3 source-lock/request/authorization。

Run3已在GPU0恢复后原子消费并成功完成；Guard post-release和独立GPU0 postcheck均通过。下一scope仍须新建one-shot authorization并现场复核。

此前外部GPU0 blocker已经解除，执行目标恢复active；科学readiness仍为`BLOCKED_WITH_REASONS`，因为四个accepted roots尚未形成。
