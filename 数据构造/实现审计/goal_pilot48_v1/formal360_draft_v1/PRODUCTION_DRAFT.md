# Formal360生产草案：结构已整理，Stage2待审批，不能执行

依据canonical《数据构造方案》D2–D5、D6–D10、D12–D20、M2/M3/M10完整相关章节；原文件未修改，读取SHA256为5b24d53718c44fb2a67e79b817c6c4904b82bacf62d4e642ce49470e980b32f9。本文仅文档/结构验证，不生成scene、candidate、prefix、raw或模型。结构检查通过不等于科学Gate、Stage2 seal或formal授权。

## 1. 草案清单与不可变分母

planned_slots.draft.json包含56个提出的slot条目：40 primary、每族rank1–4共16个inactive reserve；ID目前是draft proposal，不是已分配执行slot。每family primary固定如下；F1–F4各复制一份，产生20/8/12独立roots，对应180/72/108目标raw。

| primary rank | split | difficulty |
|---|---|---|
|1|train|clear|
|2–4|train|medium|
|5|train|crowded|
|6–7|validation|medium|
|8|test|clear|
|9|test|medium|
|10|test|crowded|

每family=2clear/6medium/2crowded；split×difficulty为train1/3/1、validation0/2/0、test1/1/1。每root3structured intents×r_pc/r_inv_path/r_inv_motion各一次=9真实成功轨迹；40×9=360，不把derived views、失败、reserve planned slots、pilot48或历史Mouse计入分母。

pilot若未来promotion，只能Stage2明确批准后进入formal train，raw semantics不变、补足9条、全量revalidation、显式promoted_from_pilot，不能重复计数；任何pilot永远不能进入validation/untouched test。本草案不选择任何promotion，所有primary origin=fresh_formal。

## 2. 尚不能冻结的字段

实际scene_seed、master seed/分配算法、executable generator版本、asset实例池/许可/物理属性、role schedule/display permutation、formal_attempt_budget_v1、stop_condition、数值阈值/H-step grid都pending，JSON使用null而非伪数值。Stage2批准前不能采seed试探，随后失败不能偷偷换seed/difficulty。

F2新布局只有有限planner等开发证据，完整物理root/正式生成器仍pending。F3稳定抓持到完整V/H/回原位/多realization的正式生成器仍pending。F1/F4的局部development成功也不证明10-root formal难度与角色网格可执行。四family的formal success rate全部unknown/null，不用微任务成功率推算formal root率，不把API通过率写成科学有效率。

已有开发代码只能作为implementation impact review的lineage候选：F1专用parent source、F2受控inside/carry-release、F3已版本化grasp/world/event修复、F4新B资格/root/variation接线。需逐项审查、固定文件与asset hash之后才能绑定formal generator；不能把旧task ID当完整实现映射。canonical文件和已封存Stage0/旧raw都不更改。

## 3. 确定性场景生成器输入合同

共同参数：slot ID/family/rank、固定seed、generator与source/asset registry版本、split/difficulty或activation继承值、camera/robot/physics固定配置、布局采样规则、可见像素和独立抓取要求、非目标物体、initial arm/gripper状态、role/referring-expression映射、scene-family/super-root grouping。生成器必须一次性从这些输入产生scene/provisional programs，不能边规划边挑容易candidate。

family参数见draft JSON generators.required_parameters：

- F1：3active同类对象+共同容器+2similar distractors+1背景障碍；跨root identity/位置轮换，同root共同target不变。
- F2：1main object+box/scale/pot或stand三facility+2distractors+1背景；设施位置轮换，三互斥区域成功谓词、carry/release模型和统一物理release Gate。
- F3：1main bottle、original pad、2similar bottles、central region、1–2普通干扰；V=±z_table/H=±x_table，VVHH/VHVH/VHHV、共享首V、同最终瓶位/rest/gripper；必须基于realized motion/contact而不是command判定。
- F4：共同X+tray、A/B/C三对象与三slots、1–2distractors；common_X后ABC/ACB/BAC，role-symbol/object/slot跨root置换，同root映射不变，原completion stability/tie和neutral/noninterference。

清晰/中等/拥挤的投影宽度范围是canonical初始工程参考，不是自动formal acceptance数值。最终可见性/碰撞/阈值必须由pilot支持、Stage2统一冻结，不能按candidate/split临时调节。F3/F4语义不变；r_inv不能切臂或采样频率，P仅属于指定r_pc cohort。

## 4. Stage2与Stage3的严格顺序

Stage2审阅和所需feasibility/prefix动作也要对应独立批准及有限budget，本文无此授权。

Stage0已封存为带失败证据完成；本草案不重开Stage0，也不把4/4 accepted roots误设为Stage0完成条件。Stage1真实48条及其必要Gate由机器证据另判，草案不将其置true。

1. 审批并冻结56个planned specs（实际seed、generator等已填）；在任何formal feasibility前不可变。
2. 每primary按固定seed生成scene和3 provisional programs，分别task/physical feasibility。planner solvability单列，不能反向删candidate。
3. 任一false/unknown：terminal+原因+保留所有证据，停止该slot，按同family reserve rank激活，不改失败slot。
4. 全部可行才冻结candidate universe、observable/oracle task tree；生成/冻结canonical prefix和关联hash，最后写candidate_frozen_root_spec。
5. Stage2 seal前形成40个active candidate-frozen specs；未激活reserve仍只有planned条目，不能提前生成objects/candidates/current/hash。此阶段封存data+mechanism-eval程序、verifier/controls/预算/source和test政策。
6. 新明确Stage3 collection授权后，才逐root采3r_pc+3r_inv_path+3r_inv_motion。每branch fresh scene重建和全anchor验证；同current只一个candidate universe，必要时更严格scene-family/super-root split。
7. 9条全部通过原子验收才accepted；不足9只能incomplete，不按部分成功进入balanced denominator。
8. dataset全部40/360且分割/配额/lineage一致后机器finalize、人工仅查看允许内容、hash索引与seal发布。后续derived H/P/controls或模型工作仍需其授权/Gate，不自动开始。

## 5. 单root原子验收清单

- planned slot身份、seed/source、resolved split/difficulty、candidate universe/task trees/prefix freeze都完整。
- 3candidate task/physical feasibility均通过；9次fresh reconstruction与current RGB/state/anchor验证完整。
- 3intents×3不同真实realization，9raw+9receipts+9family verifiers；raw-first26维250Hz，N actions/N+1 states，command/target/drive/realized state分流。
- r_pc共享确切prefix bytes/steps，禁止padding凑P；两个r_inv保持arm/program/order/250Hz，不是假raw重采样。
- F3/F4九份final-state-equivalence及root级共同终态比较，包含relevant/non-task object、arm/gripper、duration/action count和统一tolerance版本。
- current/anchor、duration/length/pause/planner/branch泄漏、对象角色与候选顺序balance无hard failure；所有attempt、recovery、fresh-scene/cleanup/orphan完整。
- raw/sidecar/MP4（若inspection policy要求）/receipt全部hash校验；最终group divergence更新后先写finalized branch再root/index，内存/磁盘一致；中间和失败历史不覆盖。
- raw、candidate、root/scene-family、derived H/K/mask/replacement视图split原子。普通训练batch每root最多1样本，根是统计单位。

正式数值tolerances、query/timeout/retry上限、具体MP4采样/访问策略仍待Stage2；不把开发run局部常数原封不动伪装成正式冻结标准。

模型可见白名单仅current RGB/state、截至真实anchor后H的future effective setpoints、随机显示的结构化candidate语义与可见指称。normal answer-bearing instruction、selected intent/local ID、路径/branch/file名、simulator ID、planner target/phase、未来RGB/pose/contact、success/verifier truth、final state及未来mask/bbox都隐藏。observable task-tree决定compatible set；oracle tree仅审计，非singleton H不得强行branch-specific one-hot。H、cohort-specific P、K、R、诊断L与trajectory长度不能互换，root派生的所有view保持同split；当前草案不生成这些view或训练模型。

## 6. Ordered reserve与失败账

reserve split/difficulty永久写inherit_failed_slot，candidate_freeze_status=pending_activation；激活append-only receipt包含reserve_root_slot_id、replaces_failed_root_slot_id、reserve_rank、resolved_split、resolved_layout_difficulty、failed_slot_terminal_receipt_hash、activation_policy_version/timestamp/hash。不回写原reserve planned spec。candidate-frozen spec引用activation receipt；primary该字段not_applicable。

只用同family下一个未用rank，不并行试多个挑优、不覆盖原失败ID、不降R。reserve再失败继续下一个rank并保留完整链。某family四个reserve用尽仍不足10个accepted，formal_dataset_incomplete，禁止seal；增加reserve需新manifest版本及批准。

分别报告40primary/16planned reserve、实际attempted/accepted/incomplete roots、activation ranks、family attrition和失败原因。保留无Scene的Guard/no-child失败、factory失败、planner失败、physical/verifier/anchor失败；不同分母不混合。

## 7. 正式预算仅列公式，数值待批准

formal_attempt_budget_v1与现有pilot/Goal预算独立，不能动用“6000等Goal余量”开始formal。对每slot s、candidate c、realization r预先批准A_s,c,r最大attempt数；实际collection requests在scene factory之前计费，失败不退款。

```text
accepted denominator = 40*3*3 = 360
actual collection attempts = sum over attempted active slots,c,r of actual attempts
collection upper bound = sum over maximum permitted activated slots,c,r of A_s,c,r
solver problems = sum over actual outer solver invocations of goal-batch N
scene attempts = setup/creation entries (qualification/prefix/preflight/collection全部计)
action scenes = 实际执行task控制的scene集合数，setup动作另账
lease seconds = 全作业实际GPU lease区间含cleanup，独立核验
```

内部IK迭代不重复算外层MotionGen问题；10-goal batch算10，不算1。dummy warmup若跳过必须单列，若真实运行必须计费。native query provenance复用不是新solver。collection与scene不等：factory失败可collection1/scene0；prefix/preflight可scene/action>0但collection0。每job预留后执行、停止后核验实耗并reconcile，过程不能扩大上限。

族级未知成本包含generator/task-feasibility、必要资格、canonical prefix、suffix preflight、9真实rollout、有限recovery、reserve。当前不填formal数值预算和wall-time，也不按单条成功率p计算p^9（同root轨迹相关）。耗时/产率需以正式前的同范围pilot证据估计，保留不确定性并审查有限stop。

GPU设备scope继承用户当前0–7 fresh-idle规则；一卡一job、root不shard，UUID/Guard/lease/pre-post/PID/cleanup审计。formal并发调度方案待批准，不能把当前Goal串行策略自行扩成多卡formal采集授权。

## 8. Blind test与发布

Stage2/3自动collector/verifier/finalizer可以处理test slots，但model/checkpoint/metric seal前人不浏览test current/raw/MP4/derived内容。受限目录与test access ledger需要先实现；视频可以保存为受限审计资产，默认不导出给人。只有机器检查摘要可进常规进展，不泄露测试图像/轨迹/隐藏状态用于调参。

任何人工查看、debug、QA、阈值/control/representation/checkpoint选择导致test root失去untouched身份，按冻结replacement/reserve处理，不继续称one-shot。normalization程序Stage2冻结，mean/std必须待formal train生成后仅用train拟合；validation选择，checkpoint+metrics seal后一次性test，失败不能换checkpoint重开同一test。

建议发布链：draft结构review→明确Stage2授权→固定spec/registry/procedure/source→自动feasibility与必要激活→active40 seal→明确Stage3授权→raw-first逐attempt落盘→root原子finalizer→dataset配额/leakage/access/attrition审计→只读publication index/hash目录→用户授权的Git commit/push。Git发布不等于科学Gate或采集授权。所有失败与中间receipt追加保存；不得改canonical、Stage0历史或既有raw来凑360。

## 9. 本草案缺项清单

实际seed和generator代码/asset registry、每family10root balance可执行性、F2/F3完整root与variation成功证据、formal数值阈值/预算、observable task-tree/H/control程序、blind-test权限系统、模型/训练评测协议、train-only normalization过程以及Stage2/Stage3明确批准均pending。Future-content/Temporal/H-P/compression/policy科学Gate均未由此草案评估或通过。
