# F4-B实际入口预算差额，不启动GPU

本次决定允许14scene / 10robot-action-scene / 136query / 6raw，明确要求保留新root的原资格检查、不得继承A成功、不容纳额外未计数probe。以下是现有入口的审计，不是证明所有可能的新实现都无法在该预算内工作。

## 现有调用链的硬依赖

1. `Robotwin2/production_micro_gate_v1/job_runner.py:924` 的 `run_f4_development_r_pc_root` 在构造root前，要求passing template terminal和三个source planner terminals。
2. `controlled_multi_future/f4_full_program_physical_v1.py:61` 的 `build_f4_full_program_physical_spec_v1` 先按source/slot/program/seed构造planner spec，再要求terminal.spec_sha256、candidate_sha256和program_id精确一致，以及`robot_kinematic_table_world_planner_pass=True`。新B不能直接用A的三份terminal。
3. `f4_development_root_runtime_v2_2/job_runner.py` 调入V2的`_build_bound_specs`；V2逐个检查这三份terminal的真实12 target-construction +30 chain =42query账本。
4. root里的`plan_f4_full_program_suffix_from_replayed_prefix_v1`仍从新prefix实际末态重新规划，而不是自动将上述外部planner controls无条件复用。

## 直接保留现有检查、不伪造B资格的最低增量

| 项目 | scene | query |
|---|---:|---:|
| 当前proposal已计入的B root三r_pc +三motion | 14 | 136 |
| 为新B取得三份精确source planner terminal | 至少3 | 3×42=126 |
| 合计下界 | 至少17 | 至少262 |
| 相对本次上限的差额下界 | 至少+3 | 至少+126 |

这还**没有**计入新布局可能要求的physical template/isolation前置成本，不能把17/262当成已经完整冻结的替代预算。动作scene也不能简单认定仍为10。

## 本轮处理

- 不创建F4-B GPU执行manifest，不运行额外probe，不拿A回执改hash冒充B。
- B的单一布局、seed2026090604、3r_pc+3真实1.10motion、A/B相关scene-family lineage仍保留；不会把A/B拆到train和untouched test。
- 两种下一步需要明确：接受经完整调用链推导的新总预算；或审查一个将B资格规划与root内部规划合并的版本化接口，在同一真实prefix末态、相同物体状态和source lineage下安全复用controls。后一种方式必须证明资格检查未被删掉，不能仅删除旧terminal校验来凑136。
- 这是本族预算前置条件未满足，不应阻断其他族已符合条件的作业；目前其他族GPU仍受全卡忙限制。
