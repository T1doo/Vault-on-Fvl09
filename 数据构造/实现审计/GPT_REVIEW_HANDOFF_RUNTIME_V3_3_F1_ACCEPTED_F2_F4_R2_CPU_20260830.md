# GPT review handoff：F1 accepted，F2–F4 revision-2 CPU baseline

## 当前裁决

```text
BLOCKED_WITH_REASONS
accepted nonformal roots = 1/4
Stage 0 trajectories = 0
stage0_authorized = false
```

## 真实运行结果

| Family | Revision | 结果 | Planner / execution | 下一步 |
|---|---:|---|---:|---|
| F1 | 2 | complete root accepted，三branches 3/3 | 46 / 3 | 已闭合 |
| F2 | 1 | task/physical collector contract fail | 0 / 0 | 仅剩r2 |
| F3 | 1 | canonical shared-V physical Gate fail | 16 / 0 | 仅剩r2 |
| F4 | 1 | common-X grasp target construction fail | posthoc 4 / 0 | 仅剩r2 |

四张GPU3–6均独立lease/cache/PID，所有Guard无timeout、orphan0、post-source-lock与GPU release通过。

F1 accepted证据：793-step byte-identical prefix；red/green/blue planner15/15；raw N/N+1为4163/4164、4048/4049、4210/4211；true-inside/non-target/contact/stable/gripper/rest全部pass；root finalizer accepted。Evidence tree=`47114cbc…444a0`。

## 最后三项revision-2

- F2：保留spawn layout；dynamic can只在task/physical以50×250 Hz同pose linear+angular、upright、support height/contact、sleep、XY/drop验收。Held suffix不套spawn Gate。
- F3：V=±z 55 mm、H=±x 50 mm与VVHH/VHVH/VHHV不变；每event固定7 targets `[+.5,+1,0,-.5,-1,-.5,0]`、每endpoint hold50；pose-derived linear+angular用于Gate，PhysX component velocity仅audit。
- F4：planned arm显式right；common-X采用与A/B/C相同的历史成功显式cube grasp contract；common9+每block6与order结构hard Gate；layout/tray/program/verifier不变。

Trace/raw现在强制real schema、trace_role_names、逐role10字段shape、planner N/其他N+1、pose-consistent angular stability；active/snapshot各262/262，source SHA=`bd16a349e6ded6f496e5daab62616bf36e3d4fac57cfe8b66488bd98d2381e2a`。多代理最终P0 sweep未发现剩余确定性P0。

## 下一安全动作

发布本byte-equal baseline后，为F2-r2、F3-r2、F4-r2各签一次fresh bundle，并在不同fresh-idle GPU并行运行。任一失败即对应family terminal；无revision-3。只有4/4 accepted后才生成`approved=false` Stage 0审批包，仍不执行Stage 0。

首选入口：

- `F1_STRICT_PREFIX_ROOT_RUNTIME_V3_3_REVISION2_ACCEPTED_REPORT_20260830.*`
- `F2_ROOT_RUNTIME_V3_3_REVISION1_FAILURE_AND_REVISION2_REPAIR_REPORT_20260830.*`
- `F3_ROOT_RUNTIME_V3_3_REVISION1_FAILURE_AND_REVISION2_REPAIR_REPORT_20260830.*`
- `F4_ROOT_RUNTIME_V3_3_REVISION1_FAILURE_AND_REVISION2_REPAIR_REPORT_20260830.*`
- 四个`*_EVIDENCE_MANIFEST_20260830.json`
- `RUNTIME_V3_3_PARALLEL_ROOTS_REVISION_LEDGER_SNAPSHOT_20260830.json`
- current registry/readiness、代码审阅快照、日志149–152。
