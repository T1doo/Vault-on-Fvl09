# Attempt8 CPU 修复与执行包失效说明

## 实际终端

Attempt8 已在 GPU0 通过实时 Guard 并取得 lease。三项 F1 任务物理可行性均通过；正式分支尚未开始时，canonical prefix 复用检查触发了：

```text
SameCurrentMismatch.__init__() missing 1 required positional argument: 'receipt'
```

本次实际消耗为 fresh=5、action=1、collection=0、solver=0、GPU lease=518 秒。child、GPU 上下文和 lease 均已清理；没有 green/blue motion raw，也没有新的正式 branch。

## CPU 修复

1. `native_f1_orchestrator.py` 的 sealed-prefix current 不一致路径现在生成并保存结构化 `SameCurrentMismatch` receipt，包含 component differences、phase、artifact/fresh current hash 和 receipt hash。
2. 同一文件的 branch reuse 路径现在从 `realization_spec_by_program[program_id]` 读取 realization，并对仅有 `slot_id` 的合成 root 使用兼容的 root identity；不再引用未定义的局部变量。
3. 新增 sealed-current mismatch 回归，确认错误类型、comparison 和落盘 receipt 均可验证。

## 验证

以下 CPU 套件通过：

```text
test_family_entry
test_f1_motion_receipt_integration
test_first_wave_launcher
test_launcher_recovery
53 tests, 53 passed
```

当前修复后的 source bundle 为 `2d6735bd2142c65e3de556a460bd8a019c76e8125789ede0087b862e207afbb5`；attempt8 批准 manifest 仍绑定旧 bundle `f6e3fa5d...`，因此该历史批准包不能继续执行。旧 manifest、授权、raw、receipt 和账本均保持原样，没有以新 hash 覆盖历史授权。

## 真实合同影响

`ATTEMPT8_PREFIX_BINDING_COMPARISON.json` 显示：sealed prefix 的 reconstruction source 为 `574a205b...`，fresh scene 为 `c8dcac07...`，且 anchor 的 `physics_config` 比较失败。这个 mismatch 发生在 attempt8 的 source/config transition 下，不能通过改 receipt 或跳过 current 检查解决。

因此当前恢复 root 仍为 incomplete：旧六条和 red 后置复核保留，green/blue 未执行。累计恢复账本为 fresh/action/collection/solver/GPU=`23/10/1/0/2217`，原 cap 剩余约 `5/5/2/64/4983`；剩余额度不足以假定能够重新生成合法 canonical prefix。后续必须先做 source/config compatibility 影响审查，或建立包含新 prefix 的新 root 合同；本文件不授权 attempt9，也不申请新的物理执行。
