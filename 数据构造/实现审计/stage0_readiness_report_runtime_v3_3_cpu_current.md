# Stage 0 readiness：runtime-v3_3 CPU current

## BLOCKED_WITH_REASONS

CPU/static基线、真实canonical-prefix smoke，以及F4 final layout v4的A/B/C no-action IK 3/3已经通过。F1 revision-1在红/绿planner通过后于蓝色`safe_vertical`失败，且未执行任何branch suffix；一个source-distinct revision-2统一carry-hub修复已完成CPU实现，但尚未运行。在F1–F4完整roots前仍不能启动Stage 0。

已经具备的部分：

- canonical prefix单次生成与三fresh exact replay代码；
- frozen suffix planner/execution接口；
- current/anchor、raw、verifier、cleanup与3/3 root finalizer；
- F1公平planner evidence、F2动态inside与互斥layout、F3 shared-V物理Gate、F4 no-action IK与staged blocks；
- 与GPU0–7 budget v1.1 JSON一致的有限预算及one-shot/revision/GPU guard链；
- 每卡原子lease、每job独立可写cache/HOME/TMP、PID/PGID中断清理、post source-lock与receipt原子更新；
- active和byte-equal snapshot各`256/256 tests passed`，source SHA=`40e2ef20…`。

仍缺的真实证据：

```text
F1 accepted root
F2 accepted root
F3 accepted root
F4 staged A/B/C/AB Gate + accepted root
```

当前计数：Stage 0=0、Stage 1=0、formal F1–F4=0；没有训练、H-reveal、compression或π0.5。

下一步先发布当前byte-equal baseline；随后按fresh source lock和≤1h one-shot authorization，在不同fresh-idle GPU上并行运行独立scope：F1仅剩revision-2一次，F2/F3/F4各为revision-1。四个family全部accepted以前，不生成Stage 0 manifest/budget/request。

补充：prefix-smoke run1/run2均在GPU0 busy时保持未消费，随后两轮source hardening使其source lock失效，现均明确superseded。后续每个真实launch都必须绑定当前published Vault HEAD、当前source lock与全新namespace。

Canonical-prefix smoke及F4 final-layout no-action IK均已成功；F1 revision-1失败证据、完整24-file manifest与ledger snapshot已保留。历史scope的GPU0-only授权在当时有效且不改写；新scope才使用GPU0–7 parent authorization/budget v1.1。每个下一scope仍须新建one-shot authorization并现场复核。

科学readiness仍为`BLOCKED_WITH_REASONS`，因为四个accepted roots尚未形成；Stage 0仍为0且未授权。
