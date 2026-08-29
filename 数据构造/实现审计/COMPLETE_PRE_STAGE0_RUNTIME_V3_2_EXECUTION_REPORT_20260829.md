# runtime-v3_2 完整 pre-Stage-0 执行报告

## 总裁决

`BLOCKED_WITH_REASONS`

runtime-v3_2 已完成获准的 F1–F4 有限 nonformal 工作并到达每个 family 的停止线，但没有任何一个完整三分支 real root 被接受，因此不得生成或启动 Stage 0。

## 环境与合同

- RoboTwin tracked commit：`c3ddfa8b97d5519efa828b075999bd0006778e5e`
- additive implementation：`controlled_multi_future_runtime_v3_2`
- primary action：`controller_effective_setpoint_v1_layout_v2_1`，26-D，250 Hz
- raw：`cmf_raw_attempt_v2_1_1`，严格 `N actions / N+1 states`
- current / anchor：`current_context_hash_v2` / `physical_anchor_v2`
- root：fresh-scene、task/physical 与 planner 分账、freeze once、append-only events、3/3 finalizer
- 本报告证据 commit：`cabdb51d865d9407c6b4c594b37da7a3f94bf7f5`

## Family 结果

| Family | 这轮实际完成 | 最终阻塞 | Root |
|---|---|---|---|
| F1 | dtype 修复生效；red/green 各 11/11 planner 段通过 | blue 第二个 6 cm lift planner 失败 | incomplete |
| F2 | 官方映射改为同一 `071_can/base1 + plasticbox/base2 + left arm`；三条真实 raw 均写出 | inside 掉离桌面；on 同时命中 beside；actual prefixes 不同 | incomplete |
| F3 | 12 cm grasp-lift diagnosis 通过；VVHH/VHVH/VHHV 均完成真实 raw | 首个共享 V 幅度 Gate；VHVH grasp slip/return；prefix 不同 | incomplete |
| F4 | right-arm layout 生效；common-X→tray 与 9/9 common checks 通过 | A/B/C right-arm grasp pose 返回无效标量，完整 ABC/ACB/BAC 未进入 planner | incomplete |

accepted real roots：`0`。

## 有价值但不能越界的结果

- A0 的 same-current / physical-anchor Gate 保持通过。
- F2 beside branch 独立通过，但不能替代同 root 的 inside/on 失败。
- F3 三套完整程序已经产生可审计真实 raw；这不等于 realized-motion 与 strict-prefix Gate 通过。
- F4 common-X 子任务完整通过；这不等于 ABC/ACB/BAC 或 strict block reorder 通过。
- runtime-v3_2 对 cleanup、raw timing、planner dtype、partial trace、right-arm scene layout 和 neutral pose 的工程审计明显更完整。

## 安全与机器闭包

- runtime-v3_2 GPU guard receipts：10
- timeout：0
- task-owned orphan：0
- scene cleanup records：87，全部安全
- post-release verified：8/10；另 2 次为 child 结束后外部用户进程新占卡，本任务未干预
- active / Vault snapshot：187/187 tests passed，105 个 Python 文件 byte-equal
- runtime-v3_2 JSON：165 份可解析；NPZ：28 份
- 最大证据文件：38,548,671 bytes

## 明确未发生

- Stage 0：0 条
- Stage 1：0 条
- formal F1–F4：0/360 条
- mechanism training：未运行
- `H_reveal`：`null`
- compression：未运行
- π0.5 / policy transfer：未运行

机器可读版本见同名 JSON。
