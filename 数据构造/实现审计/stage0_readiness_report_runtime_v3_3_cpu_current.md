# Stage 0 readiness：runtime-v3_3 CPU current

## BLOCKED_WITH_REASONS

CPU/static基线、真实canonical-prefix smoke，以及F4 final layout v4的A/B/C no-action IK 3/3已经通过。该F4结果只证明共同right-arm cube grasp endpoints可规划，不证明staged blocks或完整程序。在F1–F4完整roots前仍不能启动Stage 0。

已经具备的部分：

- canonical prefix单次生成与三fresh exact replay代码；
- frozen suffix planner/execution接口；
- current/anchor、raw、verifier、cleanup与3/3 root finalizer；
- F1公平planner evidence、F2动态inside与互斥layout、F3 shared-V物理Gate、F4 no-action IK与staged blocks；
- 与冻结JSON一致的有限预算及one-shot/revision/GPU guard链；
- active和byte-equal snapshot各`247/247 tests passed`。

仍缺的真实证据：

```text
F1 accepted root
F2 accepted root
F3 accepted root
F4 staged A/B/C/AB Gate + accepted root
```

当前计数：Stage 0=0、Stage 1=0、formal F1–F4=0；没有训练、H-reveal、compression或π0.5。

下一步按fresh source lock和≤1h one-shot authorization逐scope执行有限nonformal验证；先运行F1 strict-prefix root，再运行F2/F3，最后运行F4 staged/full。四个family全部accepted以前，不生成Stage 0 manifest/budget/request。

补充：prefix-smoke run1/run2均在GPU0 busy时保持未消费，随后两轮source hardening使其source lock失效，现均明确superseded。后续每个真实launch都必须绑定当前published Vault HEAD、当前source lock与全新namespace。

Canonical-prefix smoke及F4 final-layout no-action IK均已由Guard原子消费并成功完成；Guard post-release和独立GPU0 postcheck均通过。下一scope仍须新建one-shot authorization并现场复核。

此前外部GPU0 blocker已经解除，执行目标恢复active；科学readiness仍为`BLOCKED_WITH_REASONS`，因为四个accepted roots尚未形成。
