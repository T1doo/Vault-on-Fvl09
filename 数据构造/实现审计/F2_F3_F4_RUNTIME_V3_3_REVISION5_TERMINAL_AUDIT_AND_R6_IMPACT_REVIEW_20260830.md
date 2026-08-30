# F2/F3/F4 runtime-v3_3 revision-5 终止审计与 revision-6 impact review

## 裁决

`BLOCKED_WITH_REASONS`。F1仍是唯一accepted nonformal pre-Stage-0 root。F2/F3/F4 revision-5全部按single-use预算终止，失败证据永久保留；所有scene/process/GPU cleanup、orphan和post-source-lock检查通过。

## F2

三个suffix planner与branch execution全部运行；on和beside accepted。Inside只在开爪前50帧hold的第3帧出现一次角速度`0.056484 > 0.05 rad/s`，其余五项通过；最后40帧最大仅`0.018138`。抓取变换、assembly contact、opening projection和21.565mm rim clearance均稳定。

R6只增加10帧无新命令warmup，再按原阈值检查最后50帧；完整60帧仍检查finger contact、identity和unintended contact，final geometry不变。路线、target、planner、物体、arm和阈值不改。

## F3

三程序所有planner通过并执行；三条pre-open除contact-free两项外完全通过。`001_bottle/base13`原target OBB最低点穿入pad top约5.05745mm；固定actor-origin+10mm只产生理论4.94255mm gap，实际约4.34–4.71mm，仍落在PhysX contact offset。所有bottle/pad和assembly/pad/table manifold impulse均精确0，但pair-presence strict Gate正确拒绝。

R6不放宽contact Gate；使用center-aware bottle OBB与gripper assembly envelope，使两者相对max(table,pad top)都具有冻结10mm几何净空。对bottle单独需约15.057449mm world-z shift，再与assembly所需值取max。V/H、program、return 2×、xy/orientation和最终verifier均不变。

## F4

修复后的10段common prefix/high-neutral通过；A pregrasp和common-X/B/C noninterference通过；三段planner3/3。A grasp在close前被strict boundary截停：target z=.881402、实际稳定z=.895038，误差13.673mm/20.929mrad；fr_link7/8在全部50帧与table有非零接触。没有close、micro-lift、B/C或full program执行。

R6统一把A/B/C top-down pregrasp和grasp上移16mm world-z，micro仍为+20mm；来源是13.637mm collision equilibrium加2.001mm table clearance，冻结16mm。布局、prefix、arm、阈值、forbidden-contact和noninterference Gates不变；不做高度搜索。

## Evidence

- F2 tree：`98e6ea3f…d911a1`（39 files）
- F3 tree：`94299900…bf3e0`（33 files）
- F4 tree：`93228220…8dcf8`（14 files）

revision-6仍必须source-distinct、single-use、finite、recovery=0；本审计不授权Stage 0。
