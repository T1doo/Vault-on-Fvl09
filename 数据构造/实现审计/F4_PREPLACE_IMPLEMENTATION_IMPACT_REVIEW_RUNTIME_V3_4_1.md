# F4 preplace implementation impact review — runtime-v3_4_1

v3.4 并没有证明四条完整 corridor 失败；它实际是替换四个 carry-mid，然后共用旧 preplace。因此当前不能声称 layout infeasible，也不授权移动 tray、换臂或改 final target。

v3_4_1 将 candidate 的 variable-length `segments` 完整应用到 planner，固定顺序为 c1→c2→c3→c4。每个 candidate 在第一次 planner query 前比较 exact segment IDs 和 pose hash；不等时以 0 planner / 0 execution 的 infrastructure failure 终止。每个成功 segment 保存 terminal qpos、minimum joint-limit margin、within-limit 和 audit version。

第一个完整 corridor pass 才允许一次 A-only execution；A pass 后才允许同一 corridor 的 B/C planner-only preflight；B/C pass 后才可签发一个 F4 full nonformal root。四条完整 corridor 均失败才生成 layout-impact request，而不是自动修改 layout。
