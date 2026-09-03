# F2–F4 production recovery 执行计划 V1

- 日期：2026-09-03
- 状态：`ACTIVE_CPU_REPAIR_PLAN`
- 适用设计：`controlled_multi_future_f1_f4_v1_2`
- 官方 RoboTwin tracked baseline：`c3ddfa8b97d5519efa828b075999bd0006778e5e`
- 启动时 Vault HEAD：`fafeb5d21cd14edc840fa445c8a4e906a6d49584`
- Stage 0：`STAGE0_COMPLETED_WITH_FAILURE_EVIDENCE`，永久封存，不重开、不重跑、不覆盖
- 本计划不授权：Stage 1、formal 360、训练、H-reveal、compression、π0.5

## 1. 目标与完成定义

本计划不再把“规划器能返回路径”当成“数据任务已修好”。目标是把 F2、F3、F4 的现行生产调用链修到能够用少量、受控、可审计的真实物理执行判断模板是否能产数，然后才决定是否进入 Stage 1。

本计划的 CPU 部分完成，必须同时满足：

1. 每族只有一个明确的现行 production dispatcher；测试和将来的真实运行走同一个入口。
2. F2 现行物理入口调用两阶段 controlled insertion V2，而不是历史 gravity-drop/旧 release 链。
3. F3 scene identity 与物理等价分离：资产、seed、布局身份精确绑定，settle 后 pose 使用显式容差，不再要求浮点字节完全相等。
4. F3 planner Stage B 明确只提供空载机器人运动学证据，不产生抓持连续、瓶子运动或 candidate-ready 结论。
5. F4 planner receipt 明确标出动态物体和 carried-object 未建模时不能推出 physical noninterference/candidate-ready。
6. 至少一组 focused production-path E2E 覆盖 issuer/dispatcher/runner/verifier 的现行符号和失败分类；旧入口若被调用必须 fail closed。
7. CPU tests、source inventory、失败证据和下一 GPU 微资格预算被发布；CPU 阶段真实 GPU、planner、scene、physical、trajectory 计数均为 0。

只有下列真实物理证据全部出现，才能称为“四族基础模板修好”：

- F2：同一 current 的 `inside/on/beside` 三条 `r_pc` 全部成功；inside 必须通过离桌抓持、实际变换插入、盒内支撑、慢释放和最终 strict-inside。
- F3：同一 current 的 `VVHH/VHVH/VHHV` 三条真实轨迹成功，首个 V 共享且由瓶子真实运动、接触连续和返回边界验证。
- F4：同一 current 的 `ABC/ACB/BAC` 三条真实轨迹成功，过程不扰动非目标物体，最终世界状态等价。
- F1：现有 5 development roots/15 `r_pc` 保持可重放和 verifier 兼容；它们仍不是 formal 数据。

## 2. 当前事实基线

| 项目 | 当前事实 |
|---|---|
| F1 | 5 accepted development roots、15 trajectories；formal increment=0 |
| F2 | Stage 0 的 on/beside 有历史成功，inside 未通过；accepted development root=0 |
| F3 | 旧物理候选在 shared-V 前抓持/离桌/稳定性失败；accepted development root=0 |
| F4 | A-only 实际执行后 slot footprint 失败，B/C 位移超限；accepted development root=0 |
| Stage 1 | 0/48，未授权 |
| Formal | 0/40 roots，0/360 trajectories，未授权 |
| 当前 replacement smoke | 已批准但未签发任何 slot、未消费、0 queries/0 scenes/0 physical/0 trajectory |

当前 replacement smoke 的 152 queries 只覆盖 planner wiring；它不验证 F2 完整插入、F3 真实抓持或 F4 carried-object/dynamic-object collision。因此它不再作为本 recovery 的首要 Gate。

## 3. 根因与修复映射

### 3.1 F2

已证实的最早物理失败不是盒子装不下，而是物体没有可靠离桌并保持在夹爪中；旧 r09/r10 在 source 附近就出现 table contact、finger-contact discontinuity、opening projection outside 和 negative rim clearance。

当前 `can0 + box2` 的静态几何空间已经较大；`can5 + box8` 曾通过完整 planner，但真实抓持失败。资产大小与抓持/执行链必须分开判断。

CPU 修复：

1. 将 `execute_f2_controlled_insertion_physical_v2` 接入现行 production dispatcher。
2. 禁止现行入口调用 `execute_f2_inside_physical_v1`。
3. 物理合同至少需要 8 个 planner queries：3 个 approach/qualification + 5 个由 post-lift actual transform 构造的 suffix。
4. pre-lift Gate 允许正常 table support；post-lift Gate 必须证明 off-table、contact continuous 和 grasp transform stable。
5. 先保留两组 development asset pair：`can0+box2` 与 `can5+box8`，不再只凭静态 margin 宣布唯一赢家。

GPU 微资格预算：最多 4 次真实 inside execution，每个 asset pair 左右臂各最多一次；第一个通过完整 strict-inside 的模板进入同-current 三程序 root 验证。候选失败可继续，基础设施失败立即停。

### 3.2 F3

旧 asset13 实际失败集中在 shared-V 之前：grasp transform 漂移、finger contact 不连续、瓶子未离开 support；另有候选在 pregrasp execution 失败。

当前 128-recipe panel 覆盖 bottle model 15/5/4/13、双臂、上下区域、contact 0/2/4/6 和 rotation 0/5，但当前 Stage A/B 仍是 planner qualification。Stage B 重建 scene 后设置 robot qpos，并未物理附着或搬运 bottle。

CPU 修复：

1. `scene_binding` 拆成静态身份和 settle observation。
2. 静态身份继续精确 hash：asset/model、arm、seed、pad/marker nominal layout、generator/config。
3. settle observation 使用冻结容差：position 与 quaternion angular error 分别报告；超差才 fail closed。
4. 不允许用 tolerant comparison 隐藏错误 asset、错误 actor、错误 seed 或错误布局。
5. Stage B receipt 增加 `physical_grasp_continuity_proven=false`、`bottle_motion_proven=false`、`candidate_ready=false`。
6. survivor 选择保持每个 asset×arm×region stratum 最多一个，但 GPU 物理微资格优先跨 asset 分层，不按单一 stratum 的前四个顺序试。

GPU 微资格预算：最多 4 个分层候选，每个只做一次真实 `close → settle → 25 mm lift → hold → shared V → return`。至少一个通过后，才允许一次 `same-prefix × 3 fresh scenes × no-suffix` development diagnostic。失败不伪造轨迹。

### 3.3 F4

当前 planner collision scope 只有 table；A/B/C dynamic objects 不在 CuRobo world，carried block 未 attached，robot-link vs scene-object collision 未证明。历史 A-only 已观察到 A slot footprint 失败和 B/C 位移。

CPU 修复：

1. 将 planner evidence 明确分成 robot-table kinematics 与 physical scene noninterference，前者不得升级为后者。
2. 检查现有 CuRobo/adapter 是否有可审计的 dynamic world update 和 attached-object 支持。
3. 若可实现，加入 A/B/C/tray/common-X collision objects 与 carried-block attachment，并把 receipt 绑定到实际 world hash。
4. 若当前接口不能可靠支持，停止扩大 planner panel，转为最小真实 A-only/B-only/C-only/AB/AC 分段物理 Gate。
5. 保持最多一个 F4 development root，不改变 ABC/ACB/BAC、object-slot mapping 或 final-state verifier。

GPU 微资格预算：先 r01 A-only；通过后依次 B-only/C-only、AB/AC noninterference，最后才允许同一 root 的 ABC/ACB/BAC。任一步失败，停止完整 root 执行并回到布局/走廊修复。

## 4. 执行阶段

### Phase A：CPU-only production-path recovery

预算：GPU=0、real planner=0、SAPIEN scene=0、physical=0、trajectory=0。

顺序：

1. A0：append-only 封存当前零消费 replacement wave，状态为 `SUPERSEDED_UNCONSUMED_BY_PRODUCTION_RECOVERY_V1`；不删除 approval/ledger/source locks。
2. A1：建立 versioned recovery contract、现行入口表和精确 source scope。
3. A2：修 F3 scene-binding tolerance 与 planner-only claim boundary，先消除确定性 P0。
4. A3：接通 F2 V2 controlled insertion production dispatcher，并使旧 F2 executor 从现行入口 fail closed。
5. A4：完成 F4 dynamic/attached collision capability audit，选择“实现碰撞世界”或“物理微门优先”的单一路线。
6. A5：新增 production-path focused E2E 和负例；运行 focused tests，再运行受影响兼容测试。
7. A6：同步 review snapshot、发布 CPU repair review 和更新后的 Stage 1 readiness；仍不得称为 candidate-ready。

Phase A 停止条件：

- 需要改变 F1–F4 科学协议、程序、正式 denominator 或 verifier threshold；
- 发现当前资产身份、license 或碰撞文件不可确认；
- 测试只能通过降低既有物理 Gate；
- 任何命令意外初始化 GPU。

### Phase B：GPU production wiring sanity

只在 Phase A 全部通过、并取得新的精确授权后执行。每族可在不同 fresh-idle GPU 上独立运行；同一 root 不 shard。一卡一 job，每个 job 完整 Guard/UUID/lease/PID/pre-post/cleanup。

Phase B 不运行旧 1696-query full panel。只验证：

- F2 production dispatcher 确实进入 V2 full path；
- F3 real scene 能通过身份+容差 binding，planner Stage A/B claim 不越界；
- F4 选定的 collision/noninterference 路径在真实 scene 中生效。

### Phase C：bounded physical micro qualification

按 F2、F3、F4 各自预算执行。任何一族未出现至少一个可重复模板，不进入该族 development root。所有成功和失败都保留，不能挑选后删除失败。

### Phase D：development `r_pc` roots

只生成用于证明模板可产数的 development roots；不计入 formal denominator。F2/F3/F4 各先完成一个三分支 `r_pc` root。F4 总开发 root 上限仍为一个。

### Phase E：Stage 1 implementation/readiness

在申请 Stage 1 授权前实现并验证：

- 真实 `r_inv_path`；
- 真实 `r_inv_motion`；
- root-atomic 9/9 finalizer；
- F3/F4 final-state-equivalence；
- raw/video/current/anchor/failure/orphan/balance/leakage receipts；
- Stage 1 cumulative 48-trajectory exact manifest。

只有统一 readiness 为 ready 后才向用户申请 Stage 1；本计划自身不授权 Stage 1。

## 5. 汇报节奏与状态词

每次汇报必须分别使用：`implemented`、`planner-qualified`、`physically-qualified`、`generated`、`verified`、`scientifically supported`。不得把其中一个替代另一个。

里程碑汇报：

1. Phase A 文档、代码和 focused tests 完成；
2. Phase A 全量 CPU freeze 完成；
3. 每族第一次真实 GPU/物理 terminal；
4. 每族第一个完整 development `r_pc` root；
5. 统一 Stage 1 readiness。

## 6. 时间预估

- Phase A：1–2 个工作日。
- Phase B/C：GPU 可用且首批候选合理时约 1–3 个工作日。
- 四族基础 development 模板齐全：最好 3–5 个工作日。
- 若 F3 四种 bottle 均无法稳定抓持，需要新资产/抓法 impact review，额外约 3–7 天。

时间预估不是成功声明。每个阶段只由磁盘证据和冻结 Gate 决定是否前进。
