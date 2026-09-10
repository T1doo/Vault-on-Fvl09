# F1验收与单条接线：独立交叉复核

状态：`TARGETED_VERIFIER_REVIEW_PASS`。本文件只覆盖本轮修复1/2的F1源码，不重审旧历史或其他family。检查者未改被检查实现；仅新增 `test_independent_f1_verifier.py` 反例。

## 已核实的接线

- canonical D6.6要求非目标位移采用Stage2冻结阈值，D6.7要求正确identity、inside和非目标/干扰物保持。新formal spec已显式冻结3mm；`contract_for_f1()`将同一全轨迹相对t0位移信号映射到该值，正式disk verifier不再读取旧开发PROVISIONAL的10mm。缺合同直接拒绝，不以选“较严数字”代替绑定。
- `native_f1.execute_with_stage_capture()`在成熟primitive实际调用边界记录连续stage区间、执行臂、250Hz、actor/finger/link身份、真实gripper尺度；hold位置在post-prefix，path目标在safe_horizontal。独立检查对照实际effective/requested控制和frozen controls，而不是只比较总长度或总距离。
- 实际开爪检查来自 `audit__realized_left_gripper_joint_qpos` 与已冻结master范围；`gripper_command=1`但实际关爪反例已独立拒绝。
- 支撑检查不是单纯body pair：调用v8完整物理接触判定，结合冲量/分离、point/normal、world-Z法向分量与实际容器底板band；允许sleeping零冲量但真实接触，不将零冲量一律判无支撑。释放检查所有实际robot-link物理接触。
- 原始capture写盘并读回在动作前执行；每条raw写盘/scene收尾后立即调用`finalize_native_cell`，包含raw合同、identity、原始RGB/state/anchor、row0、语义/阶段和实际模型出口。单条失败时后续branch停止。跨分支current/anchor/三条r_pc前缀与变体配对仍由root完成后检查。
- `finalize_structure(write_receipt=False)`与`validate_saved_cell`提供只读复核；copy-only不再覆写旧accepted root或per-cell原件。

## 实际复现的三个缺口

在明确synthetic保存数据副本上单独调用真实 `verify_f1_disk`，没有把predicate/finalizer mock成true：

| 反例 | 首次独立结果 | 原因 |
|---|---|---|
| stable window中subject某帧移动2mm，但保存的线速度数组全零 | 错误pass | disk verifier只norm保存速度，没有从保存pose/timestamps再计算。 |
| stable window中EEF某帧移动2mm，但最后一帧及保存速度为零 | 错误pass | EEF静止仅看最后row，与合同声明的stable window范围不一致。 |
| suffix中右臂velocity目标维度18单帧改变，右q目标不变 | 错误pass | 固定非执行臂只检查6:12，遗漏18:24和右夹爪维度25。 |

这些是明确合成判定反例，不是声称既有真实轨迹出现了这些错误。三个问题已由实现者按同一既定速度阈值、窗口和执行臂定义修正，修复后本检查者重新执行四个独立反例，全部按预期拒绝；未新增物理实验或新的容差。

特别核对了运行来源：`runtime_trace.py`中primary role linear/angular velocity本来由连续pose差分生成，`*_velocity_measured=False`为设计；另有component velocity及availability mask。不能简单要求measured=True而错误拒绝有效pose-derived轨迹。独立验收应直接用已保存pose/time重算，记录来源，避免未测零值或错接保存速度冒充静止。

## 检查边界

四个独立反例已于最终冻结后重新运行，4/4通过。上表记录初次发现，不是最终状态。完整输出保存于 `INDEPENDENT_VERIFIER_CHECK.log`。

CPU fixture只用于函数联通和负例验证；未执行GPU、真实planner或机器人。新camera API readback、物理抓持/承重、真实不同realization的非hold控制等价性及实际耗时仍属于未来获批首批验证。


## 最终修复闭合证据

- `pose_rates()`直接读取world位置、wxyz姿态与对应state timestamps，从每个状态的前一状态计算线速度/角速度；检查时间正值/有限值。物体稳定窗口和EEF的hold/终态窗口均调用该函数，不再以保存零速度或component availability flag当作静止证明。
- subject使用原冻结object speed阈值；EEF使用原冻结速度与rest容差，在既定最后50帧窗口检查。2mm/4ms单帧运动对应0.5m/s，确实应被这些既有阈值拒绝。
- `right_arm_unchanged`覆盖effective action维度6:12、18:24和25，包含右臂位置、速度及右夹爪，不只检查q目标。
- 复跑命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/nfs_share/lijunhui/Robotwin2/project/RoboTwin /nfs_share/lijunhui/Robotwin2/env/bin/python -m unittest test_independent_f1_verifier.IndependentVerifierReview -v`；4项通过，6.621秒。

本定向交叉复核没有剩余已复现未修正的验收接线问题。CPU函数测试与源码核对不能替代未来新场景的真实物理通过率、原生相机/接触读回和资源实测。
