# Pilot48 最终高清交接（已暂停）

日期：2026-09-07  
远端：`https://github.com/T1doo/Vault-on-Fvl09.git`  
当前 main HEAD：`144c36b`

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

## 2. 证据与异常处理

- 所有 F1/F4 publication receipt 的源文件 hash、目标文件 hash 和完整软件解码均已复核。
- F4-BAC 标准轨迹的原 Guard 曾因外部进程占用 GPU0 在 cooldown 阶段记录 `CooldownExhausted`，原 Guard 的 `cleanup=false` 事实未改写；外部任务自然退出后追加 `hd_late_release_review_v1/OBSERVATION_002.json`，重新核实本任务 PID/PGID 已消失、GPU0 回基线并完成实际预算对账。
- 最后一条 F4-BAC 路径变化在 GPU3 上正常完成，Guard、清理和回基线通过。
- 所有本任务队列、Guard、renderer 进程已退出；当前 Goal 无 active reservation。GPU0/1/2 上若仍有任务均为外部进程，未干预。

关键交付提交：

- `50a8273`：F1 全部高清上传及暂停规则记录
- `5b75782`：F4 高清包、晚到释放证据和 publication receipts
- `144c36b`：其余 Goal 审计/失败证据/保留草案发布

## 3. 当前科学状态（不要混同为已完成）

- Goal pilot accepted：24/48；本轮视频不增加该数字。
- Formal accepted：0/360；Stage 1 scientific complete：false。
- F1/F4 的已有 pilot 输入仍是历史/开发证据；高清回放不等于新 rollout。
- F2/F3 视频是失败诊断，不能当作 F2/F3 成功资格或正式数据。
- 训练、H-reveal、compression、π0.5、formal 360 collection 均未授权/未执行。
- 当前 Goal budget（最终对账后）：used = solver 2296、fresh scenes 73、action scenes 32、collection attempts 6、GPU lease 16216；remaining = solver 3704、fresh scenes 167、action scenes 88、collection attempts 90、GPU lease 70184；reserved 全部为 0。

## 4. 暂停点与后续审阅入口

用户明确要求“都上传完毕以后先暂停一下”。因此从 `144c36b` 之后：

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
