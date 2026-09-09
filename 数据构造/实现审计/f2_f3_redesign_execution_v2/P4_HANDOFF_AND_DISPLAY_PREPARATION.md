# P4 F2/F3 交接与展示准备（2026-09-09）

本文件对应最新审阅要求，基线为 Vault commit `ec3a3c7204db92158d57648509956ae35dcdddec`。本阶段只做 CPU/file 交接，不重新执行机器人，不改变 P4 采集状态。

## 当前有效数据

- [P4 当前来源清单](P4_CURRENT_DATA_SOURCE_INDEX.json)：F2-A、F2-B、F3-A、F3-B 四个 root，共 24 格。每格列出 root/program/realization、trace/current/anchor/prefix 路径与哈希、cell/root 独立验收、scene/source profile。
- F2-A、F2-B：各 6/6，独立 root finalizer 通过；F2-B 每格保留 `lift_clearance_m=0.12`。
- F3-A：保留 P3 的 6/6，差异仅按 [兼容性审计](P4_F3A_PRESERVED_COMPATIBILITY_AUDIT.json) 标记为 metadata-only；不重采。
- F3-B：独立 root finalizer 6/6 通过；原 runner `INCOMPLETE` 回执原样保留，当前资格依据独立 finalizer 与对账文件。
- 24 格 current bundle、trace 哈希、cell finalizer 和 root finalizer 的 file-level 对账均通过；旧 raw、失败轨迹和旧回执未修改。

## 统一 48 格引用

- [P4 统一 48 格引用索引](P4_UNIFIED_48_REFERENCE_INDEX.json)包含：
  - F1/F4 24 格：`HISTORICAL_DEVELOPMENT_READ_ONLY`，只作开发/审计引用；
  - F2/F3 24 格：`P4_CURRENT_SCOPED_PILOT`，当前 scoped pilot 资格；
  - Stage1 eligible=0，`full_stage1_scientific_supported=false`，不进入 untouched validation/test。
- F1-A 的一个历史路径变体没有 root receipt，仅有 provisional branch receipt，已在索引中如实列出，不补造来源。

## 新 P4 高清展示计划

- [P4 display-only 计划](P4_DISPLAY_ONLY_PLAN.json)已建立，执行状态为 `PLAN_ONLY_AWAITING_APPLICABLE_DISPLAY_AUTHORIZATION`。
- 优先四格：F2-A `beside/r_pc`、F2-B `inside/r_pc`、F3-A `VHVH/r_pc`、F3-B `VHVH/r_inv_motion`；确认来源、布局、资产和事件标注后再处理其余 20 格。
- 目标规模：24 display scenes、48 MP4（每格 2880×1440 六视角与 960×720 前视角）。输出目录明确带 `P4_v43`，不覆盖旧影片。
- 只允许保存状态回放：禁止 `scene.step`、planner、task action、collection 和 raw 修改；画面需标注 `SAVED-STATE RE-RENDER | NOT A NEW ROLLOUT` 及 root/program/realization/trace 身份。
- 计划预算为独立 display-only 上限：4 root jobs、28,800 GPU lease 秒，production solver/fresh/action/collection 增量均为 0。该数值不是 P4 生产余额，也不是 GPU 执行批准；未获适用 display 授权前不启动 GPU。

## 阶段边界

P4 仍是 `P4_SCOPED_24_INPUTS_READY`。formal360、训练、H-reveal、compression 和科学 Stage1 均未开始。展示是否完成不改变采集资格，也不会把旧影片改写为新 P4 来源。
