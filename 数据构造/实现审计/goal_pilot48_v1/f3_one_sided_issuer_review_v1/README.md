# 独立one-sided micro pureissuer

入口 `runtime.issue_one_sided_micro.build_manifest(job_id,reservation)` / `issue_from_reservation`，只返回内存manifest；主线程实际reserve并独占发布。此模块不reserve、launch或写持久job。

父作业严格是已消费 `p48_f3_tangent_micro_001`，不是退回006：全部旧source/input先重算，原失败终端self-hash/2solver已知计数/真实失败文本、真实trace收据和文件哈希、Guard终端与已清理事实均核验。新目录/namespace为 `p48_f3_one_sided_micro_*`，已有manifest/dataset/guard/meter/cache任一存在即拒绝。

只接受最新 `f3_one_sided_escape_v2/CPU_AUDIT_V2_1.json` 精确receipt `1dde8a3aba566d83c5e4e48e227689e3ca84870f0ca113f5925c383c980201ff`、43tests、25当前源，逐条hash；独立CPU_INPUT_BINDINGS的self-hash、关联audit receipt和每个真实输入hash也核验。旧V1及初版V2审查只作为不变历史文件保留，不拿旧source锁冒充当前验证。所有源/input要求在workspace内。

新job.kind保持F3_MICRO以进入generic局部/全局计数核验，新模型使用独立variant/schema，model_eligibility_revision=2。原recipe3/route2/25mm保持；明确native负向epsilon0.1mm、无任意正上界，不生成第四稳定配方。

预算固定3solver/1scene/1action/0collection，child900秒/lease1080秒。正常6次高层start checks单列非solver（full2/pair2/restore2），GPU0–7实时idle/串行/完整Guard规则不变。测试入口v6.test_all；后续GPU实际仍须原postlift与两fresh成功，不自动sharedV/formal。

9项CPU review包括真实依赖构造与全部父表保留、错reservation/旧namespace拒绝、旧源hash冲突、新CPU source/input冲突拒绝、无mutator、实际generic dispatcher local2/meter3拒绝及3/3通过。CPU中只传内存reservation stub，临时generic输出在workspace专用临时目录清理；不形成真实预算/作业授权。`CPU_REVIEW.json`为该purebuilder源锁；旧issuer、V1/v5、V2/v6冻结源均不修改。
