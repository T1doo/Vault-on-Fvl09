# Pilot48 最终高清交接（已暂停）

日期：2026-09-07  
远端：`https://github.com/T1doo/Vault-on-Fvl09.git`  
当前 main HEAD：`ea2e17b`（本文件所在的最终交接提交）

## 1. 本次已完成的交付

本轮只做保存状态的高清回放，不重新执行成功轨迹，不新增 raw trajectory，不改变 pilot/formal 分母。

- F1：12 条源轨迹，全部生成并检查；每条包含六视角页和 front 页，共 24 个 MP4。
- F4：12 条源轨迹，全部生成并检查；每条包含六视角页和 front 页，共 24 个 MP4。
- F2：1 条失败诊断回放，六视角页 + front 页，共 2 个 MP4。
- F3：1 条失败诊断回放，六视角页 + front 页，共 2 个 MP4。
- 总计：48 个 F1/F4 原生高清 MP4 + 4 个 F2/F3 诊断 MP4。

视频目录只有 MP4，按 family、根组和 realization 分组：

`数据构造/演示视频/F1/高清多视角_状态回放/`  
`数据构造/演示视频/F2/高清多视角_状态回放/诊断_未验收/`  
`数据构造/演示视频/F3/高清多视角_状态回放/诊断_未验收/`  
`数据构造/演示视频/F4/高清多视角_状态回放/`

每个高清回放保留 head、left_wrist、right_wrist、observer、world1、world2、static_1_front_camera。六视角页为 2880×1440（每格原生 960×720），front 页为原生 960×720 裁去黑色空白，不做放大。视频带有 `SAVED-STATE RE-RENDER / NOT A NEW ROLLOUT` 标记；渲染器是 `default_native_raster`，不是原始 raytraced RGB。

### 高清视频精确位置

F1 的 24 个高清文件位于：

```text
Vault-on-Fvl09/数据构造/演示视频/F1/高清多视角_状态回放/
├── 根组A/01_标准轨迹/        F1-red|F1-green|F1-blue_{六视角,前视角}.mp4
├── 根组A/02_路径变化/         F1-red|F1-green|F1-blue_{六视角,前视角}.mp4
├── 根组B/01_标准轨迹/        F1-red|F1-green|F1-blue_{六视角,前视角}.mp4
└── 根组B/03_节奏变化/        F1-red|F1-green|F1-blue_{六视角,前视角}.mp4
```

F4 的 24 个高清文件位于：

```text
Vault-on-Fvl09/数据构造/演示视频/F4/高清多视角_状态回放/
├── 根组A/01_标准轨迹/        F4-ABC|F4-ACB|F4-BAC_{六视角,前视角}.mp4
├── 根组A/02_路径变化/         F4-ABC|F4-ACB|F4-BAC_{六视角,前视角}.mp4
├── 根组B/01_标准轨迹/        F4-ABC|F4-ACB|F4-BAC_{六视角,前视角}.mp4
└── 根组B/03_节奏变化/        F4-ABC|F4-ACB|F4-BAC_{六视角,前视角}.mp4
```

F2/F3 诊断高清文件位于：

```text
Vault-on-Fvl09/数据构造/演示视频/F2/高清多视角_状态回放/诊断_未验收/F2_inside_{六视角,前视角}.mp4
Vault-on-Fvl09/数据构造/演示视频/F3/高清多视角_状态回放/诊断_未验收/F3_抓持失败_{六视角,前视角}.mp4
```

同一 `演示视频/F1/根组A|根组B/` 和 `演示视频/F4/根组A|根组B/` 下还保留历史低清 MP4；它们没有被删除或替换。F2/F3 下的 `诊断_未验收_轨迹重建/` 也保留早期三视角示意视频。GPT 审阅高清时应优先打开上面的 `高清多视角_状态回放` 路径。

## 1A. 这个 Goal 阶段实际做过的事情

下面按“做过什么 / 结论是什么 / 是否进入正式数据”列出完整范围，便于 GPT 不把开发证据误读成科学完成：

1. **Goal 建立与证据固化。** 完整可见对话被保存为 `USER_GOAL_SOURCE.md`，并建立 `GOAL.md`、`CONTRACT.json`（Goal id `cmf_pilot48_20260907`）及 hash receipt。定义了四族 F1–F4、8 个 pilot roots、48 条 pilot 输入、正式 40 roots/360 trajectories 的边界，以及 raw-first、anchor、R=3、H/P/K、分组统计和禁止训练泄漏的规则。
2. **环境与控制面。** 在 fvl05 重新验证 RoboTwin 基础环境、CUDA 12.1、SAPIEN、CuRobo/MPLib、GPU UUID 绑定、Guard、lease、预算 meter、进程树追踪、清理和 Git 私有 Vault 发布流程。迁移来的 fvl09 假设被区分为历史证据；没有改系统驱动或公共 RoboTwin 仓库。
3. **Stage 0 封存。** Stage 0 最终封存为 `STAGE0_COMPLETED_WITH_FAILURE_EVIDENCE`：12 个 active slots、15 个历史 terminal receipts、5 个成功、7 个失败、5 条 raw/5 个必需 MP4；正式 accepted roots/trajectories 仍为 0。F1 3/3 通过；F2-on/F2-beside 通过，F2-inside 在原 ReleaseSafetyGateV10 失败；F3 共享 pre-V grasp/stationarity/support 失败；F4 没有可行 corridor。Stage 0 没有被重跑或覆盖。
4. **F1 复用与开发线。** 对已有 F1 成功轨迹做了 current/anchor/prefix、raw、N/N+1、250Hz、verifier、视频和泄漏审计；现有 F1/F4 输入被明确作为 24/48 Goal pilot inputs（其中 F1/F4 是开发/历史证据），没有通过视频回放增加样本。F1 的 12 条源轨迹后来全部做成高清回放。
5. **F2 修复与审计。** 完成 prefix-clearance 物理证据、on-release 序列化问题的 hash-bound adoption（不改 raw、不重跑）；分析 inside 的 preinsert IK、hand/box/floor/table 碰撞和抓持几何；做了 axial-roll/floor review；形成 `f2_larger_box_design_v1/` 的 CPU 大盒子设计候选。该候选需要新的 native loader、support-pair 证书、full-arm IK/route/physics 复核，尚未变成 F2 成功或正式 root。F2 inside 仍是未解决开发问题。
6. **F3 修复与审计。** 建立 upright same-asset 配方、official DenseTrace bootstrap、material-baseline review（确认 ActorBuilder 实际默认材质与场景声明不同但未擅自调参）、候选/共享 V 边界检查；执行过有限的 Stage-A/B qualification。r3063 replacement 得到真实 pregrasp/grasp/hold 支持并保存 1404 trace rows，但 lift 在实际 post-close 状态因 world collision model block 失败；后续 pair-aware saved-state model/lift plan 的 CPU/GPU 复核仍不等于 physical lift success。F3 没有被宣布为正式成功。
7. **F4 修复与审计。** 处理 F4-B root1 late-finalization receipt mismatch，完成 append-only receipt resolution，接受 1 个开发 root/3 条已有轨迹；补做 F4-B planner、candidate-bound terminal、budget/route/lineage 检查。F4 仍不是 40-root formal collection，且没有启动未经授权的 formal 360。
8. **无训练/结构审计。** 建立 no-training audit plan；S0/S1 对 24 个既有输入完成并通过（真实 primary trace→raw 字段、250Hz、N+1、planner intervals、audit arrays、38→76 state、pre/post hash 等）；发现原 `model_view.py` 只是浅层 5-field projection，严格 input boundary 仍需后续设计。S2/S3/S4 和完整科学 Stage 1 没有完成，不能把“24/24 audit pass”理解成模型训练或 Gate 通过。
9. **高清显示回放管线。** 实现 V1 saved-state replay 和 V2 native raster display，复原保存的 qpos/object poses，禁止 replay 中的 `scene.step`/task action/collection；注册全部可用相机；建立 DISPLAY 专用 meter、Guard、reconcile、publication 和串行有限队列。队列期间出现过一次 Git 全仓扫描超时、一次外部占卡导致的晚到释放，均保留原失败证据并通过独立复核解决，没有重跑已完成回放。
10. **最终视频交付与暂停。** F1/F4 48 个高清 MP4 全部抽帧检查、完整解码、hash 校验并 push；F2/F3 各一条失败诊断双页高清回放也已 push。STATE 已改成 `PAUSED_AFTER_HD_VIDEO_DELIVERY_PENDING_GPT_REVIEW`，无活动 reservation、无本任务 GPU 进程。最后把剩余未跟踪的 F2/F3/F4 审计、失败证据和明确标注为 draft/unapproved 的草案一并 push，便于 GPT 做总审阅。

## 2. 证据与异常处理

- 所有 F1/F4 publication receipt 的源文件 hash、目标文件 hash 和完整软件解码均已复核。
- F4-BAC 标准轨迹的原 Guard 曾因外部进程占用 GPU0 在 cooldown 阶段记录 `CooldownExhausted`，原 Guard 的 `cleanup=false` 事实未改写；外部任务自然退出后追加 `hd_late_release_review_v1/OBSERVATION_002.json`，重新核实本任务 PID/PGID 已消失、GPU0 回基线并完成实际预算对账。
- 最后一条 F4-BAC 路径变化在 GPU3 上正常完成，Guard、清理和回基线通过。
- 所有本任务队列、Guard、renderer 进程已退出；当前 Goal 无 active reservation。GPU0/1/2 上若仍有任务均为外部进程，未干预。

关键交付提交：

- `50a8273`：F1 全部高清上传及暂停规则记录
- `5b75782`：F4 高清包、晚到释放证据和 publication receipts
- `144c36b`：其余 Goal 审计/失败证据/保留草案发布
- `ea2e17b`：最终 STATE 暂停标志与本总交接文档

## 3. 当前科学状态（不要混同为已完成）

- Goal pilot accepted：24/48；本轮视频不增加该数字。
- Formal accepted：0/360；Stage 1 scientific complete：false。
- F1/F4 的已有 pilot 输入仍是历史/开发证据；高清回放不等于新 rollout。
- F2/F3 视频是失败诊断，不能当作 F2/F3 成功资格或正式数据。
- 训练、H-reveal、compression、π0.5、formal 360 collection 均未授权/未执行。
- 当前 Goal budget（最终对账后）：used = solver 2296、fresh scenes 73、action scenes 32、collection attempts 6、GPU lease 16216；remaining = solver 3704、fresh scenes 167、action scenes 88、collection attempts 90、GPU lease 70184；reserved 全部为 0。

## 4. 暂停点与后续审阅入口

用户明确要求“都上传完毕以后先暂停一下”。因此从最后一条视频完成、资源释放核实并写入暂停状态之后：

- 不自动恢复 F2/F3 修复、F4-B 规划、GPU 物理尝试或数据采集。
- 不重跑已完成视频，不覆盖失败证据，不改变 Stage 0 封存状态。
- 等 GPT/师哥基于以下材料重新决定下一版方案和授权：
  - `USER_GOAL_SOURCE.md` 与 `GOAL.md`
  - `STATE.json`、`budget_ledger.jsonl`、`attempts.jsonl`
  - `正式数据构造日志.md` §205–§637
  - `f2_larger_box_design_v1/`
  - `f3_material_baseline_review_v1/`
  - F4-B budget/qualification/release audit records

建议 GPT 审阅时保持三类结论分开：

1. 已生成并验证的显示视频证据；
2. F2/F3/F4 的 CPU/物理失败与修复候选；
3. 尚未授权的 Stage 1、formal 360、训练及后续科学 Gates。

本文件只是交接与暂停记录，不构成新的科学执行授权。
