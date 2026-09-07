# Tangent-unloading escape：独立模型适用性证书

这是新planner model-eligibility schema，不是重判006物理成功。旧 `support_pair_collision_v1`、`runtime/support_witness.py`、旧006失败及稳定recipe3均不修改。主线程采纳此pair/phase模型修订；本目录仅CPU实现，不签发GPU/budget。

## 原条件完整保留

锁定旧 `support_pair_collision_v1/policy.py::verify_support_witness` 的非连续支持条件是：250帧、每帧selected contact、每帧双指、全部contact信号完整、forbidden_count=0、最大相对平移漂移≤0.005m、最大相对角漂移≤0.05rad、所有world负间隙仅attached bottle/pad。这两个漂移数值来自旧模型证书本身，不是拿postlift门替换更严条件。新证书全部保留，并明确负漂移/NaN无效。

旧门还要求支持250/250。新分支并不放宽或伪造它：live实际执行原verify_support_witness并保存完整旧witness与False结果，新validator再次重跑该旧predicate且要求False。只有旧条件真通过才走原supported factory/bind_exact_pad；新schema不被旧validator接受，支持计数250也不被新schema接受。

新适用条件另增：same-pad真实支持在1–249帧，table/其它支持0帧；每帧native瓶最低点相对同一pad顶面绝对间隙≤旧native几何数值epsilon0.0001m；250连续step及250Hz时间关系；实际full single/batch均重现world-collision且所有负sphere仅指定pair。旧支持计数不足之外的任何失败不能借新分支绕过。

## 真实绑定和生命周期

`live.prepare`使用actual `scene._cmf_scene_instance_id`、独立job namespace、actual完整关节名/qpos、postclose actor/EEF、原250帧step/timestamp/contact/pose哈希、native形状、world、robot config和固定25mm目标。实际字段不存在即拒绝，不用路径或代理COM替代真实scene identity。

新policy/factory独立于旧构造器。四入口distance/collision及swept版本在MotionGen构造前绑定，robot完整世界不变；只有attached_bottle使用排除同名且同actor pad的视图。实际cache内容、全部cached回调、sphere分区在两路构造时检查。actual full single/batch起点检查2次、新pair检查2次，对比结果必须符合预期。

`SinglePlanLease`在conformance阶段允许核一致性检查；只允许一次绑定scene/plan/world的planning转换，再调用begin即拒绝；过期后所有四入口都报错。不能全局切障碍或单侧update世界。证书不提供GPU许可，仍需外部Guard/manifest/source/预算绑定。

`f3_runtime_v5.micro.run`接口与v4相同：manifest读取同一个第三recipe和108mm低pregrasp route；三次single trajectory问题上限不变。每次真实计划后仍过native fl3/fl5 Gate；lift从actual postclose精确+25mm、姿态不变。tangent plan另走该证书的native escape，不调用旧predicate时伪装成250支持。所有控制样本native不深入/下包络不下降/结束离支撑/计划actor-rise≥原20mm；仍是离散检查，不冒称连续碰撞自由。

无论成功、规划失败、native失败、执行异常，进入模型例外后finally使证书过期并重建两路**完整**attached world（pad对瓶恢复）。重新核对actual full单/批状态，各种清理仍由原scene/Guard负责。只有原物理postlift通过且恢复后的两路full有效才返回micro pass；恢复失败不能返回可继续。原始异常与恢复异常分开留证，不相互覆盖。

正常全部完成增加6个高层start-state检查（full2/pair2/restore2），不是6个新的trajectory问题；实际checker方法入口计数分别记录，不把它说成CUDA kernel launch数。kernel未profiling必须写未知。仍需2fresh微门成功，不能自动进入sharedV/Stage1/formal。

## CPU覆盖和边界

测试覆盖新旧schema互斥、支持计数保真、支持/双指/稳定/世界/时间/目标/hash拒绝、单次lease及过期、四入口mask与梯度、世界不可静默更新、native下降拒绝、v5真实run/execute最早停止和finally恢复。保存006真实250帧测试保留16/250；实际GPU-state和factory在该测试中**明确mock**，不是GPU验证。另有明确synthetic250支持正例只检验仍走旧分支，不作为数据/实验。

`CPU_AUDIT.json`绑定最终Python源和旧关键源。所有数值/物理/verifier/recipe不改；实际新policy GPU核、factory/cache、模型状态和真实25mm物理效果尚未验证。

签发前完整性收尾由 `CPU_AUDIT_V1_1.json` 取代上面初版源锁，初版文件原样保留。tangent factory在任何CuRobo/CUDA构造前纯CPU核对world shapes digest及canonical robot config hash；native执行前重新核对native瓶形状、world、完整关节名/qpos、actor/EEF与证书精确一致，拒绝计划间改变抓持变换复用证书。完整world恢复必须恰有motion_gen/motion_gen_batch且两路valid严格True；空、单路或额外伪键都不能all(empty)误过。新增对应负例，未放宽任何几何或物理条件。

执行记录：首轮torch CPU测试漏unset继承LD_LIBRARY_PATH，导入共享CUDA库I/O失败，未初始化CUDA/Scene；随后按项目契约 `env -u LD_LIBRARY_PATH` 全部重跑。一次多文件patch因Vault路径拼写错误整体未应用，复核无改动后重新应用。两者保留为CPU实施失败，不把它们记成GPU尝试。
