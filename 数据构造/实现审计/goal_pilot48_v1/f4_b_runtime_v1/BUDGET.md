# F4-B 完整调用链预算（CPU审计，未执行）

## Goal的真实goal-pose计数优先

下方646/625是旧Python API计数，**不可直接作为新Goal solver预算**。主线程明确新Goal按独立IK及MotionGen实际goal batch N计数，内部IK不重复计。

`family_runners_v3_3.py:_audited_planner_assisted_target_construction`对每个接触点调用一次batch，并在:547强制每batch恰为10个goal。当前左臂每role4个contact points，三role共12 batch，故target-construction是120个goal，不是12个。common-X cube几何构造不调用辅助planner，其10条chain仍10。

| 阶段 | 实际goal-pose问题上限 | 旧API预约保留的余量 |
|---|---:|---:|
| source Stage-A |120+15=135|另留21，但不授权扩大batch或循环|
| 三程序planner |3×(120+30)=450|0|
| 五isolation |3×(10+120+10)+2×(10+120+20)=720|0|
| 三template |3×(10+120+30)=480|0|
| strict-prefix root |10+3×(120+30)=460|0|
| 三motion |0|0|
| 合计 |2245|21，派生预约2266|

上述最多15次全三role目标构造，旧口径少计15×108=1620。旧Stage-A cap48仍作为本地API limiter，不表示可以再调用任意21个batch。新Goal主线程独立monotonic meter须双重限制真实goal数量和原有限函数调用链。没有本表以外的solver入口时2245是实际正常完整路径上界，2266的21是保留不执行的预约余量。

CuRobo构造器dummy warmup不计在此表内；主线程负责独立初始化策略跳过dummy规划及核验该策略。若保留任何warmup真实planner调用，必须新增预算和实记，不能漏掉。内部IK和迭代不是额外顶层problem，不重复乘算。

## 旧API口径的可追溯拆分

唯一B是 source blocks 和 slots 各沿table X移动-0.01m，seed2026090604；common-X/tray不变。旧A成功仅是lineage，不替代B资格。

| 阶段 | scene | robot-action scene | solver预约 | 成功路径实际最多 | collection |
|---|---:|---:|---:|---:|---:|
| 新source Stage-A |1|0|48|12构造+15chain=27|0|
| 三程序planner |3|0|126|3×(12+30)=126|0|
| A/B/C isolation |3|3|96|3×(10prefix+12构造+10chain)=96|0|
| AB/AC noninterference |2|2|84|2×(10prefix+12构造+20chain)=84|0|
| 三完整程序template |3|3|156|3×(10prefix+12构造+30chain)=156|0|
| strict-prefix r_pc root |11|7|136|10prefix+3×42=136|3|
| 三真实r_inv_motion |3|3|0|0，B自身控制1.10 retiming|3|
| 合计 |26|18|646|625|6|

DAG严格顺序：CPU新B绑定→Stage-A→三程序planner→五isolation→三template→root→motion→六格验收。失败无自动重发，额外作业由Goal总预算重新派生，不隐藏在本预约中。

计数陷阱：f4_bounded_physical_micro_v1.execute及f4_full_program_physical_v1.execute在common-X后调用initialize_trace；probes/runtime_trace.py:553把planner_query_count和queries清零。五isolation和三template合计80个prefix queries必须用独立单调meter保留，不能只读末尾suffix计数。主线程负责meter，不修改原trace语义。

root11scene=pristine1+task-feasibility3+canonical-prefix1+suffix-preflight3+branches3；后三类共7动作scene。motion每格1fresh scene，以B自身current/anchor/prefix/controls为parent，不是离线复制raw。18动作scene不冒称setup homing/open-gripper不存在，setup另行审计。

源码依据：production_micro_gate_v1/job_runner.py run_f4/run_f4_full_program_gate/run_f4_development_r_pc_root；controlled_multi_future/high_level_planner_runner_v1.py build_f4_stage_a_targets_v1和build_f4_stage_b_targets_v1；f4_bounded_physical_micro_v1.py；f4_full_program_physical_v1.py；family_runners_v3_3.py F4ControllerV3_3.plan_and_execute_canonical_prefix；root_orchestrator_v1_2.py；Vault realization_batch_runtime_v1_3/pipeline.py plan_or_load_controls。

现有旧Stage-A cap48原样预约，实际27可实记；不把旧cap改小来凑数。旧17/262只是遗漏isolation/template成本的下界。

状态：payload/runtime spec/adapter组合接口为CPU实现；所有B GPU/physical资格pending。planner仍保留原公开碰撞范围（机器人和配置table），不是附着物和全动态场景碰撞证明；CPU sweep与原physical/contact Gates不可删除。
