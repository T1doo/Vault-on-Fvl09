# Stage 0 readiness：runtime-v3_3 CPU current

## BLOCKED_WITH_REASONS

F1 revision-2已形成完整accepted nonformal root：三色planner 15/15、三fresh branches 3/3、root finalizer/cleanup通过。F2/F3/F4 revision-1分别在dynamic spawn-vs-settle合同、shared-V physical Gate和common-X grasp target阶段失败，均未进入suffix branch execution；各自最后一次source-distinct revision-2修复已完成active CPU实现。在4/4完整roots前仍不能启动Stage 0。

已经具备的部分：

- canonical prefix单次生成与三fresh exact replay代码；
- frozen suffix planner/execution接口；
- current/anchor、raw、verifier、cleanup与3/3 root finalizer；
- F1公平planner evidence、F2动态inside与互斥layout、F3 shared-V物理Gate、F4 no-action IK与staged blocks；
- 与GPU0–7 budget v1.1 JSON一致的有限预算及one-shot/revision/GPU guard链；
- 每卡原子lease、每job独立可写cache/HOME/TMP、PID/PGID中断清理、post source-lock与receipt原子更新；
- active与byte-equal snapshot各`262/262 tests passed`；新source SHA=`bd16a349…`，发布尚待完成。

仍缺的真实证据：

```text
F2 accepted root
F3 accepted root
F4 staged A/B/C/AB Gate + accepted root
```

当前计数：Stage 0=0、Stage 1=0、formal F1–F4=0；没有训练、H-reveal、compression或π0.5。

下一步先同步并发布F2/F3/F4 revision-2 baseline；随后按fresh source lock和≤1h one-shot authorization，在不同fresh-idle GPU上并行运行三个最后scope。F2/F3/F4任一revision-2失败即对应family terminal。四个family全部accepted以前，不生成Stage 0 manifest/budget/request。

补充：prefix-smoke run1/run2均在GPU0 busy时保持未消费，随后两轮source hardening使其source lock失效，现均明确superseded。后续每个真实launch都必须绑定当前published Vault HEAD、当前source lock与全新namespace。

F1 accepted root及F2/F3/F4 revision-1失败证据均已保存immutable namespace、file manifest、Guard与revision ledger。历史scope不改写；每个revision-2仍须新建one-shot authorization并现场复核。

科学readiness仍为`BLOCKED_WITH_REASONS`，因为四个accepted roots尚未形成；Stage 0仍为0且未授权。
