# F2/F3/F4 runtime-v3_3 revision-4 终止审计与 revision-5 impact review

## 裁决

`BLOCKED_WITH_REASONS`。当前 accepted nonformal pre-Stage-0 roots 仍为 `1/4`；F1 已 accepted，F2/F3/F4 revision-4 均保留为失败证据。没有 Stage 0、Stage 1、formal collection、训练、H-reveal、compression 或 π0.5。

## F2

三条 suffix planner 全部通过，三个 branch 也都进入真实执行，但均被同一个 held-contact Gate 截停。逐帧审计证明 `fl_link6` 是官方 embodiment 指定的左臂 `move_group`／EEF palm，也是 `fl_link7/8` 两个手指关节的共同父 link。允许这个经过拓扑验证的 palm 作为 gripper assembly body 后，三条 held window 中剩余非预期接触为 0。

revision-5 只修 F2 contact-body 分类：raw 的 selected-contact 与 grasp continuity 仍必须由 finger-only `fl_link7/8` 证明；palm-only contact 不能冒充抓取成功。路线、target、support boundary、predicate、阈值和 `32/3/0` budget 不变。

## F3

`VVHH` 与 `VHHV` 的所有 realized V/H、顺序、轴向、free-space contact、rest 和 EEF checks 均通过。问题发生在 return/release：当前代码把 open command 后 1/5/…/250 frames 称为 post-release，但两条 trace 在这 250 帧内仍持续 selected-gripper contact；真正 contact break 只在随后 retreat 移动约 71–74 mm 时出现。因此必须按物理脱离而不是命令时刻定义 release。

`VVHH` 的 grasp orientation drift 在最后一个 event 后仍约 4.9 mrad，到 return-preplace 才跳至 53.5 mrad；`VHHV` before-release 准确但最终 orientation error 36.0 mrad 超过原 20 mrad Gate。revision-5 仅统一修改 return：两段 cached controls 2× time dilation、original target 上方 1 cm contact-free release、pre-open stable/no-support Gate、actual qpos/contact disengagement 和以 first contact-false 为零点的 post-release sampling。final target/verifier 不变。

`VHVH` 的 reconstruction mismatch 与运行期间 active Python 文件发生瞬时重写高度一致：current hash 每次现场重算 implementation tree；后续文件恢复，另外两 branch 与 Guard post-lock 均匹配。因为失败 candidate components 未保存，精确子字段仍标记 `unresolved`。revision-5 seal child-start source SHA，capture 时 fail-closed 检查 live SHA，并保存 component-level mismatch receipt；运行期间禁止同步 active/snapshot。

## F4

A 的 7 段 CuRobo planner 已全部通过，但真实执行没有抓起 cube：最大上升仅 2.513 mm，transport contact fraction 只有 `118/750=0.1573`，且有 1 次 break。grasp endpoint 的真实 tracking error 是 84.9 mm／0.292 rad，close 在机械臂仍扫向目标时开始，结果只是推了方块。

更早的 prefix boundary 已不物理干净：command 显示 open，但一侧实际 finger 仅约 5.8 mm，并被 tray 卡住。随后 A pregrasp 路径中 `fr_link8` 直接碰撞并推移 common-X 35.4 mm；这发生在首次 A contact 之前。

revision-5 不直接尝试完整 ABC：先给 common release 增加 vertical withdraw，再回到 collision-free high neutral；用 actual finger qpos 和稳定无碰撞窗口验收 prefix boundary。A 使用此前物理上可靠的统一 top-down grasp，只有 realized grasp boundary 通过后才执行 20 mm micro-lift；必须 bilateral contact、A 上升至少 15 mm、脱离 table 且不碰 common/tray/non-target。通过后才允许设计下一版完整 carry/place route。

## 不可变证据

- F2 manifest：`F2_ROOT_RUNTIME_V3_3_REVISION4_FAILURE_EVIDENCE_MANIFEST_20260830.json`，tree `1237797e…cfd8`。
- F3 manifest：`F3_ROOT_RUNTIME_V3_3_REVISION4_FAILURE_EVIDENCE_MANIFEST_20260830.json`，tree `d5022576…06dd`。
- F4 manifest：`F4_ROOT_RUNTIME_V3_3_REVISION4_FAILURE_EVIDENCE_MANIFEST_20260830.json`，tree `9359aad0…66b8`。
