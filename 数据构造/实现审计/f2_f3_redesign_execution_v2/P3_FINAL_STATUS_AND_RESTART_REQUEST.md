# P3 当前状态与重启边界

日期：2026-09-09
最新发布：`e074023155ed8cb978a06bbc7832d199755c7934`

## 当前能证明的结果

* P2 CPU 合同、独立 finalizer、execution meter、预算账本、输入/监督隔离和 partial-root resume 已通过当前 24 项 v2 回归；v28–v30 快照均保留，旧 v1 源和 raw 未改。
* F3-A-v2 已形成完整 6/6 root：共享 V、三种 V/H 程序、path 变体、t0 RGB/state/anchor、prefix、放回、支撑、开爪、rest 和独立 root finalizer 均通过。该 root 可作为开发/审计证据保留。
* F3-B-v2 只有 `VVHH:r_pc` 首格通过；`VVHH:r_inv_motion` 两次尝试的第二 H 事件均未达到瓶体幅度/姿态门，`VHVH:r_pc` 的第一个 H 事件也未达到姿态门。F3-B root 不完整，不能登记为科研通过。
* F2-A-v2 `beside:r_pc` 四次真实尝试均在抓持后的 planner 阶段失败，没有进入支撑/释放验收；该问题不是关系标签或 finalizer 误判。详见 [F2_BESIDE_BLOCKER_REPORT.md](F2_BESIDE_BLOCKER_REPORT.md)。

## 预算事实

P3 ledger 当前无活动 reservation，已记录的 budget consumed/charged 为：

```text
fresh_scenes        15 / 28
action_scenes       19 / 28
collection_attempts 17 / 28
solver_problems    332 / 340
gpu_lease_seconds 3916 / 4800
```

其中未知 GPU lease 事故已按用户批准的 `ACCOUNTING_EXCEPTION` 处理：实测值仍为 `null`，预算按 1800 秒核销，不把 1800 秒写成实际运行时长。原 5-cell reservation 已关闭。

当前新 cell 独立通过数为 **7/24**：F3-A 六格和 F3-B 一个 baseline 格。F2/F3 仍缺 17 个科研格，原 collection cap 只剩 11，solver 只剩 8，因此当前合同不能完成原定 24 格。

## 不能直接重启的部分

* F2 beside 需要新的布局或抓持可达性设计，不能再用随机 seed、方向绕行或改标签继续试。
* F3-B motion/baseline 失败需要新的物理修复和预算；当前 solver 余量不足以完成其余 root。
* 任何新物理执行都必须先建立新 contract/预算 amendment；不能重置现有 ledger、覆盖失败 receipt，或把开发证据升级为科研资格。

## 恢复入口

恢复时应从以下原件开始：

```text
p3_execution/P3_EXECUTION_CONTRACT.json
p3_execution/P3_STATE.json
p3_execution/execution_ledger.jsonl
p3_execution/P3_PROGRESS_SUMMARY.json
Robotwin2/datasets/f2_f3_observation_contract_repair_p3/p3-f3-a-remaining5-retry1/root_receipt.json
```

F3-A 六格和全部失败历史保持只读；F1/F4 不重采。下一次授权至少需要明确：新的 F2 beside 场景/抓持方案、F3-B 物理修复方案，以及覆盖剩余 17 格和有限恢复的独立资源 cap。formal360、训练、H-reveal 和 compression 继续关闭。
