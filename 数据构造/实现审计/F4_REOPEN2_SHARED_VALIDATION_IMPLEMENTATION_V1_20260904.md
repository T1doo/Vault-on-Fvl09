# F4 reopen2 shared-validation implementation V1

日期：2026-09-04  
状态：`IMPLEMENTED_CPU_STATIC_VALIDATED_AWAITING_EXACT_MANIFEST_PREFLIGHT`

## 同路径设计

Runtime snapshot：`数据构造/实现审计/f4_reopen2_runtime_v1/`

- `manifest_contract.py` SHA=`5d5e3ed4eb02b6d6ea27cf05481c6b10c2eec49206d791f4581911e7b713046c`
- `job_runner.py` SHA=`7eaab9bc18c100e883651e1ffeaf65f388f192faab1e8620ae090c30aa34ffdf`
- `guarded_launcher.py` SHA=`3353872b247f79dc2759704af8b720dcd14ae736a4c17cab73aa76e3b54493f1`

`load_and_validate_manifest_job()` 是可执行Guard、Guard CPU preflight、runner CPU preflight和runner runtime的唯一manifest/job验证入口。不再有独立static required-field list。

它在任何lease或GPU操作前验证：

- manifest self-hash、approved/GPU/physical与final-exception status；
- 显式`run_id`、`guard_directory`、`cache_directory`；
- external-decision、Run13 zero-consumption terminal、controlled source、F4 source、RoboTwin tracked head；
- shared contract、Guard、runner文件路径和SHA；
- F4 asset map内每个active asset文件SHA；
- exact GPU0–7 scope、one-job/card、no-shard和全部禁止阶段；
- 唯一F4 job、candidate ID/SHA/dry-freeze、ABC/ACB/BAC、right-prefix/left-suffix和13项reviewed caps；
- no retry/fallback/second root/third reopening；
- output/guard/cache job paths均为新路径。

Guard `--preflight-only` 将先调用该共用函数，再以CPU subprocess调用精确runner的`--preflight-only`。Runner再次调用同一函数，解析Run9 template、三个Run2 planner terminals、candidate与三个full-program specs，并选中真实`run_f4_development_r_pc_root` dispatch。此路径不创建output/guard/cache/lease/scene/GPU context，不调用`nvidia-smi`，不消耗authorization。

当前只完成AST/import和静态常量验证。尚未生成精确approved manifest，因此尚未执行审阅要求的exact-manifest subprocess regression，也尚未发行F4 execution authorization。
