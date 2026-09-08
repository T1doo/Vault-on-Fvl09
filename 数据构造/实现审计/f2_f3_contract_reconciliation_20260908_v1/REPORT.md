# F2/F3 科学合同—实现—原始证据逐格影响报告

复核基线：`1854cb2a164fe0a1f3b13cbfa033389aa5acd6d9`。状态：`CPU_RECONCILIATION_COMPLETE / SCIENTIFIC_SEAL_NOT_APPROVED`。

本轮直接读取24条NPZ，不以旧顶层pass替代验证。24条trace当前SHA与此前高清回执所载SHA全部相同；旧STATE、CONTRACT、budget ledger、48格索引、最终完成审计与基线提交字节一致；六个关键运行源码与v14快照一致。未改任何旧接受数，未重开Goal、预算或GPU执行。

## 逐项结论与可保留内容

| 问题 | 对账结果 | 分类与后续 |
|---|---|---|
| F2四条beside | actor底部原点Z≈0.82542m，支架顶面0.825m；世界几何底部≈0.82490–0.82493m；末50帧支架接触持续存在，接触点位于顶面附近、法线近竖直，且有非零冲量 | **实际不符合**旁边语义。保留开发轨迹；真实补beside须局部物理执行，由用户后续决定，不可改标签 |
| F2四条inside | 几何中心在实际盒内XYZ，整个投影在内壁范围，顶部≈0.85644m低于0.86m；末50帧开爪、无抓持接触、速度0，盒底接触存在 | **CPU补出正证据**。保留；不可直接升级整root完成，仍缺冻结判定点/完整区域和current证据 |
| F2四条on | 几何中心在scale实际顶面范围，底部≈0.75990m对应0.760m支持面，末50帧稳定、开爪 | **CPU补出正证据**。保留；完整互斥合同仍待闭合 |
| 24条实际前缀 | effective/requested/mask及左右夹爪位置/速度drive七字段，含row0，逐字节等于各root artifact；也单独核rows1起真实动作 | **CPU补证完成**，无需重跑prefix |
| 24条row0 | 每root所有已保存组件完全相同：38qpos/38qvel、双EEF、夹爪及全部已注册role poses | **CPU补证完成（仅保存子集）**。不等于RGB/current及全物理anchor通过 |
| 原始RGB与全anchor | 最终root及复用lineage目录未发现原始RGB/current/full-anchor/camera捕获或numeric-rest工件；NPZ无RGB字段 | **证据缺失**。没有拿HD帧充数；若恢复观测须明确“重建”并决定适用性 |
| F3共享V和后缀 | 十二条共享V从实际EEF/对象轨迹按原边界和原幅度门重算全过；36个后缀事件也全过 | **CPU补证完成**。不使用缺省True，不进行物理reorder |
| F3瓶体返回/稳定 | 原始NPZ重新测量返回、速度、pad接触、夹爪打开，与已有正结论一致 | **保留正结果** |
| F3机械臂共同终态 | 两root分别6条末端位置最大差0.0684/0.0706mm、姿态差0.000248/0.000213rad；qpos最大差0.000510/0.000659；pad和marker完全相同 | **CPU补证完成（测得一致性）**。关节容差、未保存对象、预定rest目标仍缺；不宣称全世界正式验收 |
| F3预定rest | 原runner把瓶子返回误差传给rest是明确接线错误。末端距row0约0.362m，终态qvel仍有小量非零；未找到新root预先数值冻结rest | **证据缺失/待合同决定**。row0只是诊断参照，不能据此把十二条全判失败，也不能事后把测得终点定义为rest |
| A/B独立性 | F2 A/B和F3 A/B各自全部保存row0组件逐字相同，场景代码也是同一硬编码布局 | **不支持独立场景声明**。保留同一名义场景的不同cohort；完整RGB不在手，不能推出像素完全相同。独立根需求需后续决定 |
| 真实数据出口 | 24条实际state=76、future=N×26（剔除row0）、250Hz来源联通；原始RGB和current-grounded候选绑定缺失 | **仅部分联调完成**。完整四字段出口0份，故阻断而不填零图；答案/路径只在supervision/audit |

## 几何与接触判定的限制

本报告将metadata center/extents乘effective scale，再用每帧实测四元数旋转，得到保守世界AABB，并同时报告几何中心、投影、底/顶高度和末50帧接触/稳定。没有把actor原点直接当罐体中心。此AABB不是精确凸分解体积。

inside的保守AABB底边比盒底面低约0.08–0.10mm，严格零容差“整个AABB在腔内”因此为false；这不自动证明真实穿透或原研究失败。canonical允许冻结判定点/体积，当前具体绑定不完整；本报告保留原始数值，不增设epsilon制造通过。beside annulus的v3冻结半径未找到，不按数据拟合环带。

接触pairs中还存在有正分离距离、零冲量的邻近shape，因此`pair_presence=1`不是独立的承重证明。补充报告记录point separation、接触高度、normal和impulse；睡眠物体的零冲量也不能被反向当成不支撑。F2 beside的顶面落点、持续接触与非零冲量共同证实放在架上。

合成“盒上空1.5m”“支架顶面”“人为重叠区域”仅测试新CPU辅助判定，不算真实失败。未冻结annulus返回unknown，不默认pass；互斥明确要求恰好一个谓词。辅助函数不接入生产，也未改变原成功门。

## 24格影响表

所有行共用缺项：原始RGB/完整anchor/候选绑定；本表不计算新的accepted总数。

| cell | 实际前缀 | 几何/事件/终态证据 | 分项分类 |
|---|---|---|---|
| F2-A/inside/r_pc | 七字段byte-identical | Z=0.760425m，末窗v=0，stand接触=0% | CPU补出关系/稳定正证据；缺合同/观测项 |
| F2-A/inside/r_inv_path | 七字段byte-identical | Z=0.760423m，末窗v=0，stand接触=0% | CPU补出关系/稳定正证据；缺合同/观测项 |
| F2-A/on/r_pc | 七字段byte-identical | Z=0.760419m，末窗v=0，stand接触=0% | CPU补出关系/稳定正证据；缺合同/观测项 |
| F2-A/on/r_inv_path | 七字段byte-identical | Z=0.760421m，末窗v=0，stand接触=0% | CPU补出关系/稳定正证据；缺合同/观测项 |
| F2-A/beside/r_pc | 七字段byte-identical | Z=0.825424m，末窗v=0，stand接触=100% | 实际不符合beside；局部重采待决定 |
| F2-A/beside/r_inv_path | 七字段byte-identical | Z=0.825422m，末窗v=0，stand接触=100% | 实际不符合beside；局部重采待决定 |
| F2-B/inside/r_pc | 七字段byte-identical | Z=0.760431m，末窗v=0，stand接触=0% | CPU补出关系/稳定正证据；缺合同/观测项 |
| F2-B/inside/r_inv_motion | 七字段byte-identical | Z=0.760420m，末窗v=0，stand接触=0% | CPU补出关系/稳定正证据；缺合同/观测项 |
| F2-B/on/r_pc | 七字段byte-identical | Z=0.760419m，末窗v=0，stand接触=0% | CPU补出关系/稳定正证据；缺合同/观测项 |
| F2-B/on/r_inv_motion | 七字段byte-identical | Z=0.760420m，末窗v=0，stand接触=0% | CPU补出关系/稳定正证据；缺合同/观测项 |
| F2-B/beside/r_pc | 七字段byte-identical | Z=0.825416m，末窗v=0，stand接触=100% | 实际不符合beside；局部重采待决定 |
| F2-B/beside/r_inv_motion | 七字段byte-identical | Z=0.825424m，末窗v=0，stand接触=100% | 实际不符合beside；局部重采待决定 |
| F3-A/VVHH/r_pc | 七字段byte-identical | 共享V+3事件全过；瓶体回位误差=1.565mm；EEF距row0=361.68mm | 事件/返回可保留；预定rest证据缺失 |
| F3-A/VVHH/r_inv_path | 七字段byte-identical | 共享V+3事件全过；瓶体回位误差=1.548mm；EEF距row0=361.67mm | 事件/返回可保留；预定rest证据缺失 |
| F3-A/VHVH/r_pc | 七字段byte-identical | 共享V+3事件全过；瓶体回位误差=1.563mm；EEF距row0=361.69mm | 事件/返回可保留；预定rest证据缺失 |
| F3-A/VHVH/r_inv_path | 七字段byte-identical | 共享V+3事件全过；瓶体回位误差=1.520mm；EEF距row0=361.68mm | 事件/返回可保留；预定rest证据缺失 |
| F3-A/VHHV/r_pc | 七字段byte-identical | 共享V+3事件全过；瓶体回位误差=1.520mm；EEF距row0=361.72mm | 事件/返回可保留；预定rest证据缺失 |
| F3-A/VHHV/r_inv_path | 七字段byte-identical | 共享V+3事件全过；瓶体回位误差=1.467mm；EEF距row0=361.71mm | 事件/返回可保留；预定rest证据缺失 |
| F3-B/VVHH/r_pc | 七字段byte-identical | 共享V+3事件全过；瓶体回位误差=1.713mm；EEF距row0=362.69mm | 事件/返回可保留；预定rest证据缺失 |
| F3-B/VVHH/r_inv_motion | 七字段byte-identical | 共享V+3事件全过；瓶体回位误差=1.630mm；EEF距row0=362.71mm | 事件/返回可保留；预定rest证据缺失 |
| F3-B/VHVH/r_pc | 七字段byte-identical | 共享V+3事件全过；瓶体回位误差=1.550mm；EEF距row0=362.71mm | 事件/返回可保留；预定rest证据缺失 |
| F3-B/VHVH/r_inv_motion | 七字段byte-identical | 共享V+3事件全过；瓶体回位误差=1.698mm；EEF距row0=362.70mm | 事件/返回可保留；预定rest证据缺失 |
| F3-B/VHHV/r_pc | 七字段byte-identical | 共享V+3事件全过；瓶体回位误差=1.592mm；EEF距row0=362.74mm | 事件/返回可保留；预定rest证据缺失 |
| F3-B/VHHV/r_inv_motion | 七字段byte-identical | 共享V+3事件全过；瓶体回位误差=1.530mm；EEF距row0=362.75mm | 事件/返回可保留；预定rest证据缺失 |

## 对rest接线的处理

新审计在`reconcile.py`中分别从`object_pose`计算瓶体返回误差，从`eef_pose/joint_qpos/dual_eef_pose`计算机械臂测量与跨分支差异，绝不再用瓶体误差充当rest。原收集器及回执不覆盖。缺预定rest时报告缺失而不输出rest pass。

`envs/robot/robot.py:set_origin_endpose()`记录的是setup时末端；`envs/_base_task.py`在初始化时调用它。但新F3 runner的退出是相对释放位姿+x0.10m/+z0.05m，并未回原点。canonical要求共同rest，并未在新root合同给出其数值。若后来核得原定rest就是setup origin，当前末端将不满足；若存在先于rollout的另一固定rest绑定，应提供工件后CPU比较。不能用本次测得共同终点补签冻结。

## 出口联调与语义测试的边界

原`final_semantic_controls_audit.json`是规则单元测试，原样保留。新`BOUNDARY_CHECKS.json`分列合成单元测试与24条真实state/future来源检查。`inputs`只接受rgb/state/future/candidate_set，target和path不得进入inputs；缺真实RGB时明确拒绝完整导出。

目前未运行模型，未验证模型candidate permutation表现，未生成H-view或开展物理重排。共享first-V及后缀实际事件检查是audit-only原件验证，不等于模型能从可见输入识别事件；字符串compatible set规则仍不能替代实际H窗口全链路验收。

## 后续最小工作与需要决定的事项

1. 可以直接保留：24条真实运行、真实变体、前缀原件证明、F3事件与瓶体回位、48视频及展示回执。保留不等于全部成为科研接受样本。
2. 仅CPU已补完：实际prefix、已保存row0与A/B比较、F3共同V/后缀和跨分支保存终态、F2真实高度/支撑/稳定窗口、真实state/future映射。
3. 缺项先确定来源：原始current若另有存档，按身份hash查找；本lineage未找到。不能让新渲染冒充原图。完整anchor的未记录native状态无法凭pose恢复成原始证明。
4. 必须局部物理修复的已知项：四条stand-top `beside`，但不能现在只机械重跑四条——若修布局/current会影响共同场景三分支，需先核重采边界并取得相应执行授权。本轮未预留预算或执行。
5. rest和独立root：先决定/找到有前置证据的rest定义及A/B cohort用途；再判断是否需补退出或独立场景。没有将十二条F3一概判失败。
6. 在上述事项闭合之前，**不批准原48格“完整科研封存/正式360就绪”结论**。旧计数和Goal只保留为当时实现的历史事实，新科研接受总数为未裁定。

## 复核入口

- [机器总表](RECONCILIATION.json)；逐格原始测量：[F2-A](F2-A_cells.json)、[F2-B](F2-B_cells.json)、[F3-A](F3-A_cells.json)、[F3-B](F3-B_cells.json)。
- [F2接触几何补充](CONTACT_DETAILS.json)：区别邻近pairs与顶面支持证据。
- [原件身份与来源清单](PROVENANCE.json)：对照旧高清hash和1854cb2历史工件；搜索覆盖最终root与复用lineage。
- [负例与真实出口部分联调](BOUNDARY_CHECKS.json)；[用户审阅范围摘要](REVIEW_SCOPE.md)。
- 可复运行CPU入口：`reconcile.py` → `contact_details.py` → `boundary_checks.py` → `provenance.py` → `build_report.py`。只写本审计目录，不操作旧raw/状态/预算。

新检查没有一个顶层“数据全部pass”开关：完成的是此次对账，不是重新通过科学验收。
