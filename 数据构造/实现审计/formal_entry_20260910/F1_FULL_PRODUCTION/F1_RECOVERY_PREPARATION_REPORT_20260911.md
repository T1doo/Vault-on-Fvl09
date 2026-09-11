# F1 定向故障修复与恢复准备报告

状态：`CPU_READY_PAUSED_FOR_REVIEW`。本报告不授权 GPU，不修改旧 `FORMAL_DATASET_INCOMPLETE` 状态、历史账本或 raw。

## 已完成的代码修复

1. `first_wave_launcher.py` 增加 attempt 级失败分类：`engineering_error`、`recovery_consistency_error`、`copy_index_error`、`physical_failure`、`transient_execution`、`resource_unknown`、`unknown`。只有两次都被明确分类为真实物理失败的 root 才可进入 reserve；旧无 taxonomy ledger 会停在审阅，不自动升级。
2. `scene_plan.activate_reserves()` 支持显式 `eligible_failed_roots`；工程、恢复、copy/index、资源未知不再自动更换场景。
3. `native_f1_orchestrator.py` 的 recovery reuse 路径改为读取旧 canonical prefix artifact 并调用 `replay_canonical_prefix`，不重新调用 planner；严格比较 current、anchor、动作数组、prefix end 和 physical gate，写出 `recovery_prefix_binding_comparison.json`。
4. motion 路径显式记录 `S_prefix → S_motion_start`，hold 只执行一次，规划与执行边界各自留 receipt；UTF-8 已固定到实际 scene/export/portable/CLI JSON 路径。

## CPU 证据

- 定向 recovery/current 漂移、exact replay、motion boundary、失败分类、reserve eligibility、ASCII locale 中文回执测试：全部通过。
- 完整 discovery：140 项中 138 项通过；2 项是既有 F4 synthetic fixture 因缺少 `f1_verifier_contract` 的范围外错误，未由本轮 F1 修复引入。
- py_compile 通过；当前候选 source bundle：`84e6ff73938e96bc91f6146a68452e7c34140c8ab74d76a19ba5553921a8d9b1`。

## 真实失败 trace 分析

- F1_000014：green 首次超过 1e-4 m 在 row 1455、超过 3 mm 在 row 1464，均位于 `target_grasp`；同窗口有 `fl_link8`–green 接触记录及非零 impulse，保留 7 mm 失败，不放宽到 10 mm。
- F1_000001：F1-blue 的 `target_lift_mid` planner query 成功，随后 `target_lift` query 返回 `MotionGenStatus.IK_FAIL`；没有 suffix execution trace，因此只做 targeted planner/endpoint qualification，不宣称全场景不可行。

详见 [F1_FAILURE_TRACE_AUDIT_20260911.json](F1_FAILURE_TRACE_AUDIT_20260911.json)。

## 恢复包

已准备 [F1_RECOVERY_PACKAGE_F1_000013_MOTION_ONLY_20260911.json](F1_RECOVERY_PACKAGE_F1_000013_MOTION_ONLY_20260911.json)：

- 选择 F1_000013 一个完整六条来源的 root；已有 `r_pc` + `r_inv_path` 六条，缺三条 `r_inv_motion`。
- 预算上限：fresh 11、action 7、collection 3、solver 64、GPU lease 7200 秒；这是候选 cap，不是实际消耗。
- 物理执行仍关闭；需要新的明确授权、ledger、source freeze 和 Guard 才能运行。
- 不跨 root 拼接，不将其称为完整 root。

[ F1_FAILURE_CLASSIFICATION_AND_RECOVERY_MATRIX_20260911.json](F1_FAILURE_CLASSIFICATION_AND_RECOVERY_MATRIX_20260911.json) 记录了全部 F1_000001–014 的分类、14 条保留 cell 和 incomplete copy 状态。

## 当前硬边界

旧 F1 ledger 已终止，四个 reserve 不重置；本轮保留 cell 不发布为 formal 90 条。下一步只有在 GPT 审阅并批准恢复包后，才讨论建立独立恢复执行合同；本报告本身不启动物理采集。
