# F4 tray-layout impact review v4

## 结论

```text
F4 status: terminal_failed_planner_no_authorized_layout_candidate
tray impact revision executed: false
Stage 0 eligible: false
```

F4 run1与repair-1均证明task/physical contracts通过。Repair-1将carry height修正为不低于成功lift高度后，Route1/Route2仍都在`common_center_high`失败；每个route前4个chained segments成功，第5个失败。

随后对一个可能的tray-layout revision做CPU几何审计。固定：

- table x/y bounds：`[-0.45,0.45] × [-0.35,0.20] m`；
- tray asset：`008_tray/base0`，model-data half extents约`[0.15351,0.01562,0.09350] m`，保持当前orientation；
- A/B/C初始位置不变；
- 三个visual slots位置与half-size不变；
- common-X仍是完整公共子任务；
- 不允许tray遮挡slots或初始objects。

1 cm网格搜索结果：

```yaml
left_arm_region_constraint: tray_center_x <= 0
candidate_count_with_2cm_slot_and_3cm_object_margin: 0
candidate_count_with_zero_additional_margin: 0
```

去掉left-region约束后，零margin候选共60个，但最近候选中心约为`[0.24,0.06] m`，全部位于右侧；这不会解决左臂跨工作区问题，并可能继续产生路径难度/标签捷径。

因此当前固定table/object/slot布局内，没有同时满足“左臂合理工作区、tray完整在桌面、slots/objects不被遮挡”的tray位置。共享任务只允许一个tray-layout impact revision；不能同时移动slots/objects或改执行臂，所以不执行一个已知不合格的GPU layout trial。

F4 repair-1结束后，另一用户进程在guard postcheck前占用了GPU0。Task-owned process-group orphan=0、4个scene cleanup均通过，但guard按规则将GPU post-release标成`failed_cleanup_uncertain`；该外部进程未被干预。
