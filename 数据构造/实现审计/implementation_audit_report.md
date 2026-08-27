# F1–F4 RoboTwin2 实现审计报告

日期：2026-08-27

设计：`controlled_multi_future_f1_f4_v1_2` / `merged_master_v1`

当前 runtime 审计决定：`BLOCKED_WITH_REASONS`

## 1. 环境与源码

| 项目 | 结果 |
|---|---|
| repo | `/nfs_share/lijunhui/Robotwin2/project/RoboTwin` |
| remote / branch | `origin=https://github.com/RoboTwin-Platform/RoboTwin.git` / `main` |
| commit | `c3ddfa8b97d5519efa828b075999bd0006778e5e`；`source_lock_match=true` |
| 初始 worktree | clean，dirty count 0 |
| Python/env | `/nfs_share/lijunhui/Robotwin2/env/bin/python`；Python 3.10.20 |
| CUDA | project CUDA 12.1.105；torch 2.4.1+cu121；sm_86 |
| SAPIEN/CuRobo | CPU import passed；SAPIEN 3.0.0b1、CuRobo 0.7.8 |
| GPU | 最新规则允许物理 GPU0–7 中任意 independently fresh-idle 卡；已运行的 GPU4–7 environment certifications 均 passed，所有 jobs 后均释放 |

完整 source lock：`environment_and_source_lock.{md,json}`。

## 2. Family 审计结论

| Family | 官方资产 | 官方动作基础 | 项目必须新增 | 状态 |
|---|---|---|---|---|
| F1 | RGB blocks + `062_plasticbox/base3` | grasp/lift pass；place planning failed | placement repair、selector、non-target verifier | `unresolved` |
| F2 | exact `071_can/base1` + box/scale/stand | same-left-arm inside/on pass；beside planning failed | beside repair、exclusive predicates | `unresolved` |
| F3 | `001_bottle/base13` | V/H/V→H realized pass；return-pad planning failed | return repair、full sequencer | `unresolved` |
| F4 | tray + RGB blocks + yellow X + visible slots | single neutral block pass | common-X/full programs/noninterference/reorder | `unresolved` |

## 3. 最终推荐映射

- F1：不使用“红绿蓝罐头”。使用 `envs/blocks_ranking_rgb.py::blocks_ranking_rgb.load_actors` 的同尺寸 RGB `create_box`；容器候选 `062_plasticbox/base3|base5`。
- F2：共同 main object 候选 `071_can/base1|base6`；inside=`062_plasticbox`，on=`072_electronicscale`，beside 优先 `074_displaystand`、`060_kitchenpot` 备选。最终 ID 未选，因为必须由同一 object/arm 的三关系 probe 决定。
- F3：`001_bottle/base13`，质量沿用官方 shake 的 0.01 kg；V=`±z_table`，H=`±x_table`，二者均由 `move_by_displacement(move_axis="world")` 的 audited wrapper 构造。官方 horizontal shake 不等价于 H。
- F4：common tray=`008_tray/base0`；A/B/C=procedural RGB blocks；common X 使用高对比 yellow procedural box；slots=three model-visible `create_visual_box` regions。white-X v1 低对比失败已保留。

确切 env/class/function、IDs、静态 geometry、mass/collision/friction、source hashes 和 verifier signals 见 `f1_f4_implementation_registry.json`。

## 4. 特别裁决

1. F1：官方 can variants 无红绿蓝证据，首选官方 RGB blocks。
2. F2：三个官方任务没有共同 main object；`071_can` 只是待 probe 的共同候选。
3. F3：`official_horizontal_task_is_equivalent_to_H=false`；源码显示其旋转瓶子并沿 z 位移，不做 table-x 闭环。
4. F4：官方 ranking slots 是不可见坐标；tray 只有两个 functional points，三个可见 slots 必须由 project scaffold 明示创建。

## 5. Probe 与测试

| 类型 | 命令／动作 | 结果 | 输出 |
|---|---|---|---|
| CPU environment | imports + `pip check` + nvcc version | passed | environment/source lock |
| static asset audit | JSON/GLB metadata、scaled extents、texture RGB mean、source hashes | passed at static-only scope | `probe_outputs/audit_probe_static_asset_metadata_v1.json` |
| GPU availability | 两次 host `nvidia-smi` | `blocked_gpu0_busy_no_child_launched` | `probe_outputs/gpu0_availability_blocker_20260827.json` |
| additive tests | `python -m unittest discover -s tests/controlled_multi_future -p 'test_*.py' -v` | 7/7 passed | console + live log |
| F1 runtime | RGB block grasp/lift/place | failed at block→box place planning after 1,181 steps | `f1_action_probe_20260827/` |
| F2 runtime | same can/base1 + same left arm | inside/on pass；beside place planning failed | `f2_action_probe_20260827/` |
| F3 runtime | V, H, V→H + return pad | motion/contact pass；return-pad place planning failed | `f3_action_probe_20260827/` |
| F4 runtime | visible slots + one neutral block | passed；slot≈1.9 mm, return≈5.6 mm | `f4_action_probe_20260827/` |

## 6. 新增／修改文件

RoboTwin official tracked files：0 modified。新增 untracked、additive：

```text
?? controlled_multi_future/
?? tests/
```

新增 package 含 14 个 Python 文件、fail-closed base、schemas、four family program skeletons、pure signal/verifier adapters 和 probe boundary README；新增 1 个 test 文件。`git diff --check` passed。未 commit/push。

Vault 新增 `数据构造/实现审计/` 下 environment lock、registry、probe evidence、budget proposal、readiness report 和本报告；更新 `数据构造方案.md` 的实现状态与附录 D-A.4，不改变 design version、F1–F4 programs、40/360、R=3 或 5/2/3 split。

为便于外部 GPT 直接从 Vault GitHub 审代码，当前 additive source 和 tests 的 byte-equal、只读副本位于 `数据构造/实现审计/代码审阅快照/`。active source 仍在 RoboTwin 工作树；审阅修改不能直接在 Vault 副本中演化。

## 7. Budget

`pilot_attempt_budget_v0_proposal` 已生成，状态严格为：

```text
proposed_for_user_review
approved = false
frozen = false
```

由于没有新 runtime probe，cost/time 为低置信范围，不能批准或用于正式采集。

## 8. Stage 0 readiness

```text
BLOCKED_WITH_REASONS
```

原因：F1 block→box placement、F2 beside placement、F3 return-to-pad placement 均有保留的 planner failure；F4 full common-X + ABC/ACB/BAC/noninterference/reorder 未测；budget 未审阅冻结。

## 9. 下一序列

首轮具名 probes 已结束，不原地重试。新的 targeted probes 可在 GPU0–7 任意 independently fresh-idle Gate 下运行：

1. F1 block→box place planner failure diagnosis/repair design；
2. F2 same-can beside target/reachability repair design；
3. F3 return-to-original-pad planner repair design；
4. F4 common-X + one complete natural program/noninterference probe；
5. 补全 registry、budget/readiness；
6. 停止并等待用户批准 Stage 0。

任何 probe 失败都保存并停止，不换 GPU、不换 candidate、不改 threshold、不进入 Stage 0。
