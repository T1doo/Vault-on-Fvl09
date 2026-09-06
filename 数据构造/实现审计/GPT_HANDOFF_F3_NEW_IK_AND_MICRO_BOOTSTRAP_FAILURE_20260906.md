# 新F3资格真实结果与micro初始化失败：需要精确替换决定

这是用户最新链接<https://chatgpt.com/s/t_6a9d282120f881918863d7bf69035323>的继续执行反馈。该链接已完整读至结尾YAML，相关新条件范围已发布；本文件更新先前`GPT_HANDOFF_NEW_SCOPES_CPU_READY_GPU_BUSY_20260906.md`的等待GPU状态。

## 1. 已经有真实新结果，不再只是CPU检查

GPU7空闲后，F3两新recipe的6个固定IK问题全部完成。真实模型包含actual table/pad/bottle/对臂MESH及开爪锁关节，cache和FK检查通过；目标经actual→reported→原入口roundtrip绑定。

| recipe | current_control全有效解 | pregrasp | grasp | 资格 |
|---|---:|---:|---:|---|
| r3063-topdown | 23 | 4 | 6 | 通过 |
| r1401-topdown | 23 | 0 | 7 | 不通过 |

每题32个固定seed、100iterations、原位置和sin(angle/2)判据，没有追加yaw/height/seed搜索。r1401只因为pregrasp未解而无资格；不声称数学不可达，不执行它的物理门。

输出：`/nfs_share/lijunhui/Robotwin2/datasets/f3_new_topdown_qualification_v1`。

## 2. r3063单次micro发生了接线错误，责任与边界明确

我为唯一合格r3063启动了本次已授权micro。首段pregrasp规划成功，controls已完整写出；进入`_execute_planned_segment`的第一行`len(scene.trace)`时报错，**还没到`_execute_control`，没有开始机械臂控制执行**。

原因是新direct-runner漏了原production wrapper中的：

```text
capture_current
capture_anchor
initialize_trace(scene.bottle, 'left', role_actors=scene.role_actors)
```

随后finally无条件`save_trace`又因`markers`不存在报错。原terminal traceback保留了两层异常，但第一版未将保存异常独立成字段。这是我新增接线的错误，不是场景/抓取物理失败。此前23项CPU测试主要覆盖旧sequence/postlift函数，没有覆盖新`run()`的scene生命周期，预检覆盖不够。

输出：`/nfs_share/lijunhui/Robotwin2/datasets/f3_new_topdown_r3063_micro_v1`。

原terminal receipt：`15eaeb86205845cfb33b9ea6005a703198edf7bfd32436a42234ee3acb4f1664`。

保留原source、failed terminal、pregrasp plan/controls和Guard。不伪造physical trace，不把规划controls当真实动作轨迹，也不把未执行写成抓取失败。

## 3. 已完成CPU修复，但没有自动重跑

`f3_topdown_micro_runtime_v1_1/micro.py`：

- prepare/binding完成后capture current/anchor、初始化trace；断言trace首行和markers存在后才能进入任何plan/action。
- 初始化失败时不能调用executor或保存不存在的trace。
- `trace_save_error`与primary error分开保存，secondary错误不遮蔽原异常。
- unknown counter保持null，不记零。

新增`test_lifecycle.py`直接调用修复后的`run()`，使用CPU fake scene而非只测sequence callback；四项bootstrap/error/accounting回归全部通过。没有创建SAPIEN/GPU场景，没有修改原安装库、active controlled源或Gate。

本次micro实现仍保留三次**顺序**规划：pregrasp、grasp，最后才从真实close0.50/hold250后的EEF+25mm规划lift；没有提前从open状态规划lift。tracking/window比较事先定义的actual flange目标。闭爪后的attached-bottle模型保留table/pad与原buffer，若发生支持接触/近似模型拒绝必须如实记录，不关闭整张桌面。该postclose分支本次未运行，尚未实证验证。

## 4. 精确账本与资源

| 作业 | Guard / child | GPU | 耗时 | 消耗 |
|---|---|---|---:|---|
| 新资格StageA | 2660721 / 2660766 | 7 | 85.34s | 2scene、6IK、0trajectory、0physical |
| r3063 micro V1 | 2672555 / 2672571 | 7 | 67.09s | 1scene、1trajectory、1physical-attempt slot；实际arm控制执行0 |

GPU7 UUID：`GPU-4c836e67-fb8e-a993-002c-cb83b10a6ead`。两次均由实时wave选卡、原子Guard/UUID/lease启动，任务串行；其余0–6的忙卡未共享。两次scene/Guard cleanup均通过，独立host GPU7恢复14MiB/0%/P8/no compute，所有列出的PID退出。

本次新范围累计：**3scene、6IK、1trajectory query、1physical-attempt slot、0实际arm控制执行、0训练raw、0root**。

前一次全卡忙Guard2640173从未启动child，0scene/query/physical，仍保留为不消费执行预算的调度拒绝记录；它不是上述micro重试。

## 5. 需要一个明确的一次替换决定

最新决定禁止已消费job自动重发、每recipe一个physical scene。因此即使还有总量额度，我也没有把未合格r1401的physical槽偷偷挪给r3063。

建议审查以下**proposal，当前未批准**：

```yaml
scope: ONE_R3063_TOPDOWN_MICRO_BOOTSTRAP_REPLACEMENT
approved: false
preserve_original_failed_attempt: true
reuse_passed_r3063_qualification_without_rerun: true
replacement_recipe: f3-final-pose-v3-r3063-topdown-geometry-v1
changes: trace_bootstrap_and_primary_secondary_error_preservation_only
new_caps:
  scenes: 1
  trajectory_queries: 3
  physical_attempts: 1
  IK_queries: 0
  training_raw: 0
  roots: 0
cumulative_if_approved:
  scenes: 4
  IK_queries: 6
  trajectory_queries_max: 4
  physical_attempt_slots: 2
automatic_retry_after_this: false
execute_unqualified_r1401: false
lower_two_candidate_confirmation_rule: false
shared_V_or_full_root_execution: false
```

它不增加原总上限，但改变了physical槽的候选用途，需要明确批准。若替换成功，也只能保留r3063单候选正结果，不自动声称“两候选确认”或进入shared-V/root。

## 6. 其他工作线没有被冒报完成

- **F2**：内移布局完整CPU支撑、配对、初始/持物双臂几何和beside/inside/on互斥已通过；新binding/候选坐标和attached→released状态合同已实现。实际IK/route checker中的选择性can-table支撑、released-can/open-gripper切换仍pending，没有F2新GPU manifest或新3IK作业。原inside5/5只保留历史意义。
- **F4-B**：当前直接入口为新candidate补三份精确planner资格，至少比14/136多3scene/126query，即至少17/262；还未计可能新增template/isolation成本。见`F4_B_ACTUAL_ENTRY_BUDGET_GAP_REVIEW_20260906.md`。不以A回执改hash冒充B，也不删Gate凑预算。需要完整预算重审或验证过的资格/root规划合并接口。
- **F1/F4既有数据**不动；开发6root/27raw、18个pilot候选格保持。Stage1=0/48、formal=0/360，训练/H-reveal/compression/π0.5仍未授权。

统一状态：`STAGE1_READINESS_AFTER_NEW_F3_QUALIFICATION_MICRO_FAILURE_20260906.json`；日志§496–§504。
