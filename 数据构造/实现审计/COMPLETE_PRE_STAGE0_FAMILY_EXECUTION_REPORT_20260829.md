# Complete pre-Stage-0 family execution report

## 通俗结论

```text
A0：通过
F1：三候选物理可行，但planner未通过；2轮repair耗尽
F2：固定can无法完整进入固定box；物理不兼容
F3：pad和preflight修好，但真实抓瓶后的lift失败；2轮repair耗尽
F4：common-X两个route都到不了center-high；没有合规tray layout
Stage 0：BLOCKED_WITH_REASONS
```

因此没有达到`READY_FOR_USER_REVIEW_BEFORE_STAGE_0`。本轮没有运行正式Stage0。

## Family结果

| Family | Task/physical | Planner | Real execution | Full programs/root | Terminal |
|---|---|---|---|---|---|
| F1 | 3/3 pass | 三candidate均在Float/Double接口失败 | 0 | 0/3 | failed_planner，2 repairs exhausted |
| F2 | fail | 0 query | 0 | 0/3 | can/box full-OBB incompatible |
| F3 | pad-support-v2 pass | 14/14 preflight成功×2 | 1次进入真实execution | 0/3 | prefix_lift failed，2 repairs exhausted |
| F4 | pass | Route1/2均前4段成功，第5段失败×2 runs | 0 | 0/3 | no compliant tray layout candidate |

## 机器计数

```yaml
family_gpu_scope_invocations: 9
planner_queries_recorded:
  F1: 0
  F2: 0
  F3: 28
  F4: 20
real_controlled_execution_started:
  F1: 0
  F2: 0
  F3: 1
  F4: 0
timeouts: 0
task_owned_orphan_count: 0
recorded_scene_cleanup_failures: 0
missing_root_cleanup_receipt_count: 1
accepted_real_roots: 0
```

F4 repair-1 child结束后，另一用户进程PID 1171759占用GPU0。Guard precheck时GPU0为空；postcheck出现该新外部进程，所以post-release verified=false并停止后续GPU工作。Task-owned process-group orphan仍为0，四个F4 scene cleanup均通过；未杀或干预外部进程。

F1 run1因旧JSON serialization bug在最终root receipt写入时崩溃，未保存逐scene cleanup records；其guard仍证明task-owned orphan=0且GPU release通过。后续8个family runs均保存了scene-bound cleanup receipts，记录中的cleanup failure为0。

## Versioned repairs

### F1

1. NumPy receipt serialization；
2. procedural block half-extents provenance。

最终task/physical 3/3通过、freeze once，但planner触发Float/Double接口错误。随后公共planner chain已改为float32供后续family使用；F1没有越过repair预算重跑。

### F2

未执行伪repair。固定can最小完整直径约65.1 mm，固定box strict cavity短轴52 mm；full-OBB inside不可能。

### F3

1. 根据真实footprint扩大original pad并建立scene-layout v2；
2. real trace使用与A0一致的1e-9秒float representation tolerance。

最终14段planner preflight成功，但真实execution在prefix lift失败。

### F4

1. Safe carry height不再低于已经达到的lift height。

两个route仍在center-high失败。CPU layout grid未找到左臂区域内不遮挡objects/slots的tray位置，因此未执行无效的第二repair。

## 证据入口

- F1：`probe_outputs/nonformal_F1_three_branch_root_seed20260829_run3_repair2/`
- F2：`probe_outputs/nonformal_F2_workspace_three_branch_root_seed20260829_run1/`
- F3：`probe_outputs/nonformal_F3_release_full_program_seed20260829_run3_repair2/`
- F4：`probe_outputs/nonformal_F4_common_full_program_seed20260829_run2_repair1/`
- F2 impact：`F2_PHYSICAL_COMPATIBILITY_IMPACT_REVIEW_20260829.*`
- F4 impact：`F4_TRAY_LAYOUT_IMPACT_REVIEW_V4_20260829.*`
- Stage0 Gate：`STAGE0_PREPARATION_GATE_FAILURE_20260829.*`

## 明确未执行

```text
正式Stage 0：0条
Stage 1：0条
360条正式数据：0条
模型训练：无
H_reveal裁决：无
compression：无
π0.5：无
```
