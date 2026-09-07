# Pure tangent micro issuer

入口 `goal_pilot48_v1.runtime.issue_tangent_micro.build_manifest(job_id, reservation)`；别名 `issue_from_reservation`。仅返回内存manifest，**不reserve、不atomic写出、不launch**。主线程先按Goal实际预留，再传入kind/job_id/exact CAPS/event_sha256，检查返回值后独占发布。CPU tests只传显式内存stub，未保存其manifest。

新job namespace必须 `p48_f3_tangent_micro_*`，所有manifest/dataset/guard/meter/cache路径都需未占用。预算3solver/1scene/1action/0collection，child900s、lease1080s；正常至多6个高层start-state检查单列（full2/pair2/restore2），不是额外solver问题。所有0–7 fresh-idle/串行/Guard/UUID/cleanup规则保持，GPU实时状态不由issuer保留或代验。

完整核验并继承已消费006所有source/input绑定；006必须仍为2solver的原失败、known accounting、原错误和已清理Guard。然后采用显式runtime_v2迁移入口，旧source表不丢失。实际test_module仍为 `f3_runtime_v5.test_all`。同一稳定recipe3/route2/lift25，不生成新配方、不开放shared V或formal。

只认可 `CPU_AUDIT_V1_1.json` 的精确receipt `91d2e0566e1da4619c359ce06aae1fb09a1904d1cbf065aaf2ec377fb3512c50`、36tests、21条当前source并逐条重新hash。旧CPU_AUDIT仅作为未变历史输入保留，不能拿其旧source锁当新版验证。另绑定tangent/v5目录所有Python与JSON/README、新issuer及其测试、006所有实际输出（包括physical_trace/实际COM/模型）和支持影响审查。builder拒绝任何父子source hash冲突。

5项独立CPU tests通过：真实依赖构造且旧表全保留/STATE账本字节不变、错reservation拒绝、旧namespace拒绝、无mutator调用、篡改最新CPU seal拒绝。`CPU_REVIEW.json`留证；测试不等于GPU验证或签发。原v5/tangent代码及21源锁未被本issuer工作修改。

签发前generic dispatcher复核修正：初版自定义kind会绕过现有F3局部规划计数对账。现保持job.kind=`F3_MICRO`，新模型只用model_variant和model_eligibility_schema标注。未修改冻结runtime_v2/common/v5。新增直接运行真实generic job_runner.main的两个CPU例子（仅meter/runtime为明确fake）：local trajectory_queries=2而meter=3时accounting_complete=false/exit1；正常3对3为true/exit0。共7tests通过，新封存 `CPU_REVIEW_V1_1.json` 取代初版issuer源锁，初版不覆盖。仍无reserve/持久manifest/GPU执行；临时CPU fixture终端仅在工作区专用临时目录中产生并随测试清理。
