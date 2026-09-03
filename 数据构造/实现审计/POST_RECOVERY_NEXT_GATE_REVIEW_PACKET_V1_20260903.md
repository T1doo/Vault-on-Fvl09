# Post-recovery next-Gate external review packet V1

日期：2026-09-03  
状态：`PROPOSAL_ONLY_NOT_AUTHORIZATION`

这份材料把下一轮需要审阅的选择固定下来，避免再次出现“先跑大搜索、失败后再解释”。它不是 GPU、Stage 1 或数据收集授权。

## F2：只换抓取来源，暂不改场景布局

官方 `071_can` 元数据把 contact 0–7定义为侧面抓取，把8–15定义为顶部抓取。Run3两次失败均使用旧 contact0/rotation0，且均在接触前出现140–212 mm tracking误差。

建议下一 Gate：

1. 固定四个 strata：`can0+box2 × left/right`、`can5+box8 × left/right`。
2. 保持现有V5 scene layout，先隔离抓取策略影响。
3. 每个stratum只枚举官方top-contact 8–15；每个contact调用一次10-rotation planner batch，共最多8 batch calls。
4. 按 `(contact_id, rotation_index)` 选择最低planner-success姿态并立即exact freeze。
5. 对该姿态只做一次3-query `pregrasp→grasp→25mm lift` chain；失败不fallback到下一姿态。
6. 物理前仍最多4 candidates、每stratum一次；pregrasp/grasp tracking超过5 mm或0.05 rad时禁止close。
7. 至少2个不同candidate通过才freeze；连续2个同类失败立即停。

预算提案：最多44 planner queries、4 selection scenes、4 physical scenes/MP4、0 accepted/formal trajectories。Proposal SHA：`aa05bfeef85d67c5d396182977af8852f2733d4f737bb945116f018db3de7594`。

## F3：不用搜索，冻结四个rotation1新tuple

旧四个terminal tuple都为contact0/rotation0。建议保持原asset/arm/region/scene，只把rotation改为下一个lexicographic `rotation1`，因此不是重跑旧candidate：

| 顺序 | Stratum | 新recipe |
|---|---|---|
| 1 | bottle15-left-lower | `r0005` / `3638a9e9…` |
| 2 | bottle5-right-lower | `r1445` / `90a1cfd4…` |
| 3 | bottle4-left-upper | `r2165` / `f6d56955…` |
| 4 | bottle13-right-upper | `r3605` / `b6b1e41a…` |

每个candidate只执行一次3-query Stage A与7-query lift-anchored Stage B，总planner上限40。至少2个planner survivor才进入最多4次physical；至少2个physical pass后才允许最多一次same-prefix×3 fresh-scenes×no-suffix diagnostic。

Proposal SHA：`0645a46c72c3b87bdebca19c2cf21db36784498817b7eb5d82a0543ca92b89e9`。

## F4静态修复审计

`plan_f4_full_program_suffix_from_replayed_prefix_v1` 内 `total_before` 现定义于line 382、使用于line 418；AST证明赋值在同一线性函数体中先于使用。文件SHA=`f9f12de9f23e784fa1fa600aaa3b9e2ac27e4226d3fea8b84c466230a4f67ea8`。

这只能证明明显NameError已修正，不能证明root通过。Run12后默认仍禁止F4 replacement；审阅者必须明确决定是否重新开放一次。

## 请求审阅者明确回答

1. 是否按上述精确F2预算授权？若否，请返回具体candidate/预算修订。
2. 是否按上述精确F3四tuple和预算授权？若否，请返回具体tuple/预算修订。
3. 是否允许一次F4 post-terminal root replacement？默认答案为否。

Stage0重跑、Stage1、formal360、训练、H-reveal、compression、π0.5继续禁止。Machine packet：`POST_RECOVERY_NEXT_GATE_REVIEW_PACKET_V1_20260903.json`，payload `ab682283dc22a3e5627dc24735b2206d68d7428f370b74ea8b5134a7af899318`。
