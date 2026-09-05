# 本轮总交接：真实微门/路线结果、同一证据审计与隔离CPU实现

完整读取用户最新链接 t_6a9bdf43fa348191b706338935fd5287（21742字符，无附件下载链接），按其精确决定执行。原文和结构化决定已落库，不重复复制历史。F4保持已接收，不重跑、不重复审批或计数。

## 1. 本轮真实运行结果

| 工作 | 实际消耗 | 结果 |
| --- | --- | --- |
| F3现有V1.1一次micro | 28 queries / 8 scenes / 2 physical attempts | 两候选pregrasp通过，grasp均失败，未闭爪；micro 0/2 |
| F2有限transit panel | 6 queries / 2 planner-only scenes / 0 physical | D0通过，U/D与R0/R1/R2首段均IK_FAIL |

两次都在commit/push和两轮fresh GPU快照后启动；F3用GPU3、F2用GPU1，严格串行。计数、scene cleanup、Guard/lease/cache、task-owned进程和GPU baseline全部核验通过。没有额外重试、候选替换、R3/R4、inside重跑或新root。科学失败没有被记成基础设施失败。

### F3：已越过旧的pregrasp问题，但仍未抓取

- r3063和r1401各Stage A 3/3、Stage B 7/7；r0861和r2526各Stage A首query失败，未进入物理。
- 两次物理只消耗各3个planning query。r3063在grasp窗口row706首先触发fl_link7与pad物理接触；r1401在row572首先触发闭爪前瓶位移超限。
- 两者pregrasp都pass，grasp都fail，close_executed=false；因此没有25mm lift、post-lift确认、shared-V或no-suffix，更没有训练raw/root。
- qualification=22 queries/6 scenes；physical=6 queries/2 scenes，合计28/8。全部counter完整，job error=null，负结果正确exit1。
- Guard1222530 / child1222639；GPU3 UUID=GPU-d5b84492-c467-0080-206f-2456cef0c338；207.30秒。postcheck15MiB/0%/P8，无task PID残留。
- 证据：F3_MICRO_TERMINAL_PUBLICATION_20260905_V1_1.json；原job receipt=20c565b29ae612f9cf9b7bf04493d0dc46b4c4fc921101e358a4028baa785ee4。

注意：full-window Gate在一段动作执行完成后审查整段，再决定是否继续/闭爪，不是逐物理步实时急停。没有把检测器说成模型修复。

### F2：不是只有hub不好解，固定放置目标也没有解出

| test | 结果 | live delta | 该scene累计before→after |
| --- | --- | --- | --- |
| D0 当前C正对照 | Success | 1 | 0→1 |
| D1 直接U/preplace | IK_FAIL | 1 | 1→2 |
| D2 直接D/release | IK_FAIL | 1 | 2→3 |
| R0 U→D→U→N | 首段U IK_FAIL | 1 | 0→1 |
| R1 H_low→… | 首段H_low IK_FAIL | 1 | 1→2 |
| R2 H_current_orientation→… | 首段H_current_orientation IK_FAIL | 1 | 2→3 |

- 每个test均恢复相同sealed qpos/EEF/actor，不清零scene counter；absolute_limit=before+len(targets)。路线内部使用真正chain qpos；首失败立即停。不是把累计1+2+3反复相加。
- D0成功的position error约9.16e-7m、rotation error约2.24e-6rad；其他五项均valid_query=true、MotionGenStatus.IK_FAIL。内部attempts10仍是单次plan_single内部尝试。
- 已解决的TMPDIR、metadata中心、table plane、异常计数保持有效；inside5/5及其原SHA未变。Controls保存为planner_controls.npz，未执行。
- Guard1245482 / child1245622；GPU1 UUID=GPU-414c52ba-72c6-fc45-95d6-1e9750bbc21b；69.22秒。postcheck14MiB/0%/P8，无task PID残留。
- 证据：F2_BOUNDED_TRANSIT_TERMINAL_PUBLICATION_20260905_V1.json，receipt=8d04f3e03c4b0979ef785f67440a96a4ef1d1998c0f10d5e5e64128d72f4fe77。

没有成功路线，因而没有选择R0或把它伪装成资格通过，也没有生成依赖winner的F2 root执行manifest或继续写死18-query预算。

## 2. 结果之后已做的CPU工作：不换候选，复用同一失败证据

F2_F3_SAME_EVIDENCE_MODEL_AUDIT_20260905_V1.json，receipt=c8f7a0ca47926b569189b274b250f680ea32985dc8469cafb09ec8ad43555790。

报告按要求的八项顺序审计joint/qpos、base/world、EEF/tool、spheres/meshes、ignore pairs、table/pad、对侧臂和command/realized时间线；绑定相同失败trace、URDF、config、planner源码。没有新solver/GPU/scene，也没有重新判定旧trace的Gate。

具体发现：

1. 配置中的六个左臂joint名称与planner cspace前六项一致，EEF link和move_group都是fl_link6。trace的38维qpos使用同一已验证索引；完整运行时joint-name枚举没有序列化，报告明确保留这一限制。
2. 两新候选grasp段command/realized最大关节误差仅约0.01716/0.01344rad，而瓶子最大位移分别约20.18/45.80mm。并非所有失败都能归结为旧的巨大关节跟踪误差。
3. active CuRobo world初始化只有table，没有pad和bottle；受控路径中未发现update_world调用。物理场景却发生finger-pad/finger-bottle作用。这是具体的规划世界覆盖缺口证据。
4. 左臂collision model未列入右臂link；sphere/mesh与self-ignore定义已记录，但没有把这个潜在缺口宣称为本次两个失败的已证实原因。
5. planner table与physics table源参数不同，但处于不同坐标表达，未未经变换就宣布尺寸错误；精确mesh包络覆盖也仍未证明。
6. F2配置planner-base下C/U/D距离约0.532/0.659/0.636m，URDF平移长度和的松上界约0.824m。距离不能证明不可达；结合D0成功、U/D失败，应研究固定放置姿态/抓持变换与joint/collision约束，而不是继续随机换hub。

下一合理边界：F3先提出同一候选下planner/physics world与允许接触语义的最小版本化修复；F2提出固定U/D姿态约束的有限辨析或经审阅的目标/布局影响方案。新GPU验证、终点/物体/arm变化或阈值变化仍需明确决定；本轮52/19许可均已消费。

## 3. 公共CPU实现已落地，但不冒充已部署/已物理验证

隔离checkout：
/nfs_share/lijunhui/Robotwin2/tmp/cmf_downstream_cpu_20260905

分支codex/cmf-downstream-cpu-20260905；最终commit=05acc6625ee5e3d32c335ecac77c5939e3f912df（74bf087首版、80b1f27补显式protocol binding）。只在本地隔离分支提交，没有push到官方公共remote。代码byte-identical副本在Vault downstream_cpu_source_v1_20260905。

26/26 CPU tests通过。DOWNSTREAM_CPU_IMPLEMENTATION_REVIEW_20260905_V1.json，receipt=442523b57e588517a35b796c231cd664386b3669696067c01beadf1d1303ab63。

除了独立TwoPhasePublisher，还将修复接入原root_orchestrator_v1_2的隔离副本collector.py：原branch写入改为receipt.provisional.json；finalizer计算在deepcopy上完成，随后发布正式receipt.json，再写root、最后publication index。5个完整collector合成场景测试验证立即/延迟分歧、分支失败、中断、磁盘不一致，并核验重复登记不变；不是只手造最终receipt。原active collector未改。差异见ISOLATED_COLLECTOR_PUBLICATION_DIFF.patch。

| 模块 | 已实现和验证 | 仍需明确区分 |
| --- | --- | --- |
| TwoPhasePublisher | 从磁盘provisional调用真实旧finalizer，在副本算divergence，finalized分支→root→最后index；立即/延迟分歧、未齐、中断、重复登记、磁盘不一致六场景通过 | index是publication_complete，不授予阶段/物理验收；尚未替换active collector |
| Realizations | F1/F4 spec builder、operation executor、SAPIEN motion/trace bridge、raw/video writer及pairing接口 | 具体family scene/anchor/verifier绑定仍需收口；没有新realization GPU/真实轨迹 |
| 变体proposal | 来自已封存F1/F4实际suffix targets，共12个操作提案；非关键运输z+15mm或统一duration×1.10 | 数值是待审proposal，不是物理可行保证；没有改critical target、程序或arm |
| Budget | 当前operation调用链每realization F1=11、F4=30 planner cap，prefix replay无新planner | 不是已批准完整family collection budget；实际绑定后仍需整体源锁/Guard预检 |
| 分级matrix | development3、pilotA6、pilotB6、formal9；绑定scientific protocol与profile version；重复raw/view/错variant/错program/混root等拒绝 | 不把CPU fixture或未授权数据登记为阶段accepted |

运动变体是改变下一次真实执行的planner commands，不是重采样已有raw后充作新realization。variation规则在同一cohort各program之间相同，不按ABC/ACB/BAC给不同参数或pause编码。

## 4. Stage 1/Stage 2清单已经生成

downstream_cpu_artifacts_v1_20260905：

- STAGE1_48_CELL_ELIGIBILITY.json：48个显式cells，含family/A-B/intent/realization/原证据/新采集需求/缺失原因/授权状态。
- 9格只有candidate_for_pilot_reuse：F1最先两accepted roots的6个r_pc，F4 A的3个r_pc。不是9格accepted；是否能复用仍待阶段eligibility裁决。其他已有development不删除、不自动晋升。
- Stage1 accepted仍0/48；A/B每root只要求相应6条，不再要求formal9/9提前完成。
- STAGE2_PENDING_SLOT_SCHEMAS.json：40primary+16ordered reserve，5/2/3及difficulty配额正确。seed/planned spec/current/candidate freeze保持pending/null；没有虚构物理成功或hash，normalization只列train-only程序约束，无拟合数值。
- F1_F4_REALIZATION_CPU_PROPOSALS.json：12个源码派生的操作方案和source bindings，全部collection_authorized=false。

## 5. 统一状态与下一执行入口

Development仍6roots/18trajectories：F1=5/15、F4=1/3，F2/F3=0。F4已收工，不重新审批或重跑。Stage0封存，Stage1=0/48、formal=0/360；训练/H-reveal/compression/π0.5未授权。

统一readiness：STAGE1_READINESS_AFTER_F3_MICRO_F2_TRANSIT_CPU_20260905.json，receipt=eff81bf4877b3f2ef5148a80116485a333090e4929f9674d1ad372ff3ff55439。

下一轮请聚焦同一失败证据下的模型/固定目标修复与有限验证方案，不再增加候选扫描或重复工程排障。公共CPU接口和family绑定可以在隔离目录继续收口，不需要每个helper单独往返审批；但它们不能成为绕过真实Guard或提前采集Stage1的入口。
