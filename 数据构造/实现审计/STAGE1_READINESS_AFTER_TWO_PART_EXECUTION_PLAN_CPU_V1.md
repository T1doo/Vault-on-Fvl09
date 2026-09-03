# Stage 1 readiness after two-part execution-plan CPU work V1

日期：2026-09-04

统一状态：`NOT_READY_F2_F3_QUEUED_F4_CPU_READY_FOR_REVIEW`

Formal accepted仍为`0 roots / 0 trajectories`，Stage 1不可开始。

| Family | 当前状态 | 下一步 | 授权已消费 |
|---|---|---|---:|
| F1 | 5个development `r_pc` roots；缺real r_inv与atomic 9/9 | 后续独立设计/授权 | — |
| F2 | 11-query planner-only Gate保持原文件与哈希，CPU preflight pass | driver连续两轮恢复后首先执行 | 否 |
| F3 | V1未消费supersede；预算完整V2 CPU preflight pass | F2 clean postcheck后执行V2；本job no-suffix=0 | 否 |
| F4 | physical qualified；Runtime V2 CPU lifecycle与13负例通过 | 等待新外审批准或修改一个root proposal | 否 |

## 驱动与执行顺序

最后一次实测仍为`nvidia-smi`无法与driver通信。恢复后必须先连续两轮、间隔至少
10秒取得完整8卡映射与process状态；然后严格串行：

```text
F2 → clean GPU postcheck → F3 V2 → clean GPU postcheck
```

F4即使获得后续批准，也不得与F2/F3偷跑或共享卡。

## 保持禁止

Stage 0 rerun、Stage 1、formal 360、training、H-reveal、compression和pi0.5
全部为false。F2通过后仍须先实现/审阅controlled-insertion root V2；F3通过后仍须
先完成独立3-scene no-suffix Gate和candidate-bound/arm-parametric root接口。
