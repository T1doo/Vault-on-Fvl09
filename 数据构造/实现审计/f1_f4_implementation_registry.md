# F1–F4 RoboTwin2 实现映射注册表（静态审计版）

状态：`runtime_probe_partial_blocked_with_reasons`

源码：RoboTwin `c3ddfa8b97d5519efa828b075999bd0006778e5e`

正式数据：否；Stage 0 数据：否

机器可读完整字段见 `f1_f4_implementation_registry.json`。本文件只给出审计裁决和人类可读映射；GPU0 忙，所有真实渲染／planner／物理 probe 均保持 pending。

## 结论总表

| Family | 官方资产是否足够 | 官方动作是否足够 | 必须新增 | 当前状态 |
|---|---|---|---|---|
| F1 | 官方 RGB blocks + plastic box 映射明确 | grasp/lift 已通过；block→box place planning 失败 | placement repair、三选一、非目标位移 verifier | `unresolved` |
| F2 | 同一 `071_can/base1` 已实测 | 同一左臂 inside/on 通过，beside place planning 失败 | beside repair、互斥 predicates、support audit | `unresolved` |
| F3 | `001_bottle/base13` 已实测 | V/H/V→H realized motion 与 contact continuity 通过；回原 pad 失败 | return-to-pad repair、event verifier seal | `unresolved` |
| F4 | yellow X、RGB A/B/C、tray、visible slots 均可见 | single A neutral-to-neutral block 通过 | common-X/full programs、三 block noninterference/reorder | `unresolved` |

## F1 特别裁决

`071_can` 官方可用 IDs 为 `[0,1,2,3,5,6]`，直径约 64–82 mm、高约 96 mm。离线 GLB texture RGB 均值集中在米色／红色范围，没有机器证据支持稳定的红／绿／蓝三类；在渲染审阅前更不能凭 model ID 猜颜色。

因此 F1 首选官方 `blocks_ranking_rgb` 的 procedural RGB blocks：同一 root 内三个 block 共用同一个随机 half-size，颜色明确为 `(1,0,0)/(0,1,0)/(0,0,1)`，抓取方法为 `Base_Task.grasp_actor`。公共容器候选为 `062_plasticbox/base3` 或 `base5`。静态几何支持 block 可容纳性，但真实三物体邻近抓取、容器放置与非目标不动仍待 GPU0 probe。

## F2 特别裁决

- `place_cans_plasticbox`：`071_can`；
- `move_can_pot`：不同 family 的 `105_sauce-can`；
- `place_object_scale`：只从 `047_mouse/048_stapler/050_bell` 抽样；
- `place_object_stand`：从六类对象抽样。

所以官方任务不能直接拼成“同一物体”。当前共同 main-object 候选是较小且 metadata stable 的 `071_can/base1` 或 `base6`；最终 ID 必须由同一 arm 的 box/scale/beside 三项 probe 裁决。目标候选为 `062_plasticbox`、`072_electronicscale`、优先 `074_displaystand`（`060_kitchenpot` 作为 dynamic-articulation 备选）。

互斥 predicates 的输入源已定位为 subject/reference pose、functional point、contact 和冻结 region geometry；数值阈值尚未冻结。

## F3 特别裁决

`001_bottle/base13` 是首选静态候选：约 `68.7 × 247.9 × 67.6 mm`，8 个侧向 grasp contact poses、1 个 functional point，metadata `stable=true`，官方 shake 质量设为 `0.01 kg`。

table frame 在当前代码中与 world frame 对齐：table center 位于 `[0,0,0.74+table_z_bias]`，x 沿 1.2 m 长边、y 沿 0.7 m 宽边、z 向上。`Base_Task.move_by_displacement(..., move_axis="world")` 可表达 table-x/table-z 位移。

`shake_bottle_horizontally` **不等于 H**：它先绕 y 旋转瓶子，之后仍用 z displacement 和 orientation alternation 摇动，没有 `±x_table` 闭环平移。项目必须新增 central-pose closed-loop V/H，并使用 realized EEF、bottle pose、gripper contact continuity、主/偏轴位移与 central-return error 验证。

## F4 特别裁决

- common tray 候选：官方 `008_tray/base0..3`；每个只有两个 functional points，不能直接提供 common-X + 三个 slot。
- A/B/C：官方 procedural equal-size RGB blocks。
- common X：通过官方 `create_box` API 创建的 project white block，明确标记为 project scaffold。
- 三个 slots：通过官方 `create_visual_box` 创建的 project visible regions；该 API 只有 render component、没有 PhysX collision，适合作为视觉标记，实际 success 由 object pose/region/contact 判定。

官方 `blocks_ranking_rgb/size` 的三个 target 只是坐标，不是可见 slot，不能直接用于 F4 visual grounding。neutral-to-neutral block、已放物体不干扰、统一 arm 和 completion stability 仍待 GPU0 probe。

## 共享 API 与物理边界

- `create_actor(convex=true)`：dynamic/static PhysX body + multiple convex collision mesh + visual mesh；
- `create_box`：box collision + render shape；官方 RGB block 未显式 set mass；
- scene 默认：250 Hz、static/dynamic friction `0.5/0.5`、restitution `0`；
- grasp/place：`Base_Task.grasp_actor`、`place_actor`、`move_by_displacement`、`back_to_origin`；
- realized EEF：`Robot.get_left_ee_pose/get_right_ee_pose`；
- object state：`Actor.get_pose`；contact：`scene.get_contacts`／`check_actors_contact`。

## 当前 blockers

1. GPU0 忙，无法完成渲染截图与 runtime PhysX 属性读取。
2. F2 同一个 `071_can` 的三关系、同 arm 和联合场景尚未验证。
3. F3 单 V、单 H、V→H realized trajectories 尚未生成。
4. F4 visible slots 与 neutral-to-neutral block 尚未执行。
5. per-model 上游资产来源在本地 metadata 中未单独列出；只能确认仓库和 `assets/objects/README.md` 的 MIT 声明。

## 2026-08-27 runtime probe 更新

- GPU4–7 分别通过 CUDA tensor、CuRobo import 与官方 `Render Well`，退出后全部回到 12–14 MiB、0%、P8、无 compute process。
- F1 deterministic head current 明确显示 RGB blocks 与 plastic box；动作 probe 完成抓取和约 10 cm 抬升，green/blue 位移分别约 `4.3e-7 m / 0`，但 block→box place planning 失败。
- F2 使用完全相同的 `071_can/base1` 和左臂在 fresh scenes 中完成 inside（XY 误差约 2.08 mm）与 on（约 0.44 mm）；beside place planning 失败。
- F3 single V、single H、V→H 全部执行；四个 event 的 contact fraction=`1.0`，正负幅度约 45–53 mm，central return error 约 2.7–6.7 mm。最后回 original pad 的 place planning 失败，因此 motion core supported、完整 root unresolved。
- F4 v1 的 white X 因白桌面低对比被保留为 hard-failure evidence；v2 只改 X 为黄色后 current visibility 通过。单 A neutral block 成功，slot XY error≈1.9 mm、neutral return error≈5.6 mm。
- runtime body evidence：procedural blocks 0.01 kg/1 box collision；F2 can 0.05 kg/22 convex shapes；F3 bottle 0.01 kg/7 convex shapes；project box/scale/stand/tray 当前 probe 使用 static bodies；visible slots 为 render-only、无 PhysX collision。

因此本 registry 仍不能把 `stage0_readiness` 改成 ready；F1 place、F2 beside、F3 return-to-pad 和 F4 full-sequence/noninterference 是明确 blockers。
