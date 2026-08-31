# Stage 0 Smoke Execution Report V1

## 总裁决

`STAGE0_TERMINAL_NOT_SEALED`。

12个预注册attempts全部获得终止回执，但canonical finalizer因F2基础设施错误拒绝Stage 0 seal：`stage0_completed=false`。本轮不得重跑或现场修复。

```text
terminal attempts: 12/12
PASSED: 3
FAILED_WITH_EVIDENCE: 9
generated raw trajectories: 3
generated MP4 videos: 3
formal trajectories: 0
```

| Family | 结果 | Raw / MP4 | 失败边界 |
|---|---|---:|---|
| F1 | 3/3 PASSED | 3 / 3 | red、green、blue verifier全部通过 |
| F2 | 3×FAILED_INFRASTRUCTURE | 0 / N/A | planned root spec缺少冻结`scene_layout`，三个task audit均`F2FrozenLayoutConfigurationError` |
| F3 | 3×FAILED_EXECUTION | 0 / N/A | canonical prefix pre-V boundary失败：stationarity、grasp stability/contact与无pad/table support |
| F4 | 3×FAILED_PLANNER | 0 / N/A | v13四corridor均真实planner失败，Stage 0按manifest shared blocker终止 |

F1实际计数=`46 planner/3 execution/0 recovery`；F2=`0/0/0`；F3=`7/0/0`；F4 Stage 0=`0/0/0`（其前置v13已有22个candidate queries）。所有job cleanup成功、orphan=0、GPU释放确认。

三条F1 MP4均通过文件与receipt hash，并实际解码首尾帧：red 417帧、green 409帧、blue 423帧，25fps、320×240，含initial/final frames。其余attempt没有生成trajectory，因此正确标记`video_not_applicable_no_trajectory`。

Canonical finalizer artifact是authoritative，但明确：`stage0_completed=false`、`3 success / 9 failure`、`3 trajectories / 3 videos`。Stage 1、360 formal、training、H-reveal、compression和π0.5均未运行、未授权。

## 下一步审阅重点

1. F1可否作为Stage 1候选，但仍需遵守新批准；
2. F2只修manifest/root spec的冻结layout wiring，不重定义任务；
3. F3是否进入grasp/prefix物理impact review；
4. F4是否进入预注册layout impact review，而不是继续无限corridor retry；
5. 未经新批准，不运行任何Stage 1或replacement root。
