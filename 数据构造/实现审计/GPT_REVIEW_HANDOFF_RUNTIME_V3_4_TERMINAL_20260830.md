# 给GPT的runtime-v3_4 terminal审阅交接

请锁定私有仓库`https://github.com/T1doo/Vault-on-Fvl09`的main最新HEAD，先读：

1. `Idea/项目核心Idea.md`
2. `数据构造/数据构造方案.md`
3. `数据构造/实现审计/COMPLETE_RUNTIME_V3_4_DIAGNOSIS_FIRST_EXECUTION_REPORT_20260830.md/json`
4. `数据构造/实现审计/MULTI_GPU_SCHEDULING_AUDIT_RUNTIME_V3_4_20260830.json`
5. `数据构造/实现审计/RUNTIME_V3_4_TARGETED_SCOPE_RECEIPT_RECONCILIATION_20260830.json`
6. 四份runtime-v3_4 failure evidence manifests
7. 三份`RUNTIME_V3_4_FORENSIC_*`
8. `f1_f4_implementation_registry_v3_4_current.*`
9. `stage0_readiness_report_runtime_v3_4_current.*`
10. `数据构造/正式数据构造日志.md`第182–185节
11. `数据构造/实现审计/代码审阅快照/`

当前必须维持`BLOCKED_WITH_REASONS`，accepted roots=1/4，Stage0明确禁止。

请重点独立判断：

- F1：是否只需把4个target-construction batch queries纳入reported suffix count，然后做一次shared regression replacement；
- F2：0.0793rad/s pre-release spike是应停止并做grasp/release-target impact review，还是旧pre-release Gate也错误承担了final-stability职责；注意本轮新safety Gate根本未到达，且execution budget已消费；
- F3：0 planner/0 diagnostic execution的软件ID alias失败能否允许一次replacement authorization；若允许，应保留F3 IDs并在diagnostic outer finalizer中显式免除final-state-equivalence，而不是伪造D3 family；
- F4：四个carry-mid已全部可达、A_preplace全部失败；candidate3/4 runtime与contract不完全一致。下一步是否必须直接layout impact review，还是先允许一个纯planner、严格落实lower-preplace的replacement；任何tray/arm/layout改变需要什么批准；
- F2 cleanup：如何修复inner scene cleanup已pass但outer aggregate因异常未返回而误写`failed_cleanup_uncertain`的receipt传播问题；
- 当前应做一个单次`runtime-v3_4_1 postmortem hardening`，还是停止该版本并重新设计更小的integration test。

请给出一个完整、有限、一次性的下一工作包和明确授权边界。不要把本handoff理解为自动retry或Stage0授权。
