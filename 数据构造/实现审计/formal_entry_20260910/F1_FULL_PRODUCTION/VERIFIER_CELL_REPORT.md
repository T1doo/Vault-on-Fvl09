# F1 正式验收与逐 cell 独立门修复

本报告对应本轮 CPU 实现；没有初始化 GPU、执行 SAPIEN 场景或新增真实轨迹。成熟抓取、运输、开爪、退出动作仍调用原 F1 primitive。

## 1. 3 mm 与 10 mm 的适用关系

Canonical `数据构造方案.md` D6.6 要求三个 realization 的非目标 active objects 移动量低于 Stage 2 冻结阈值，D6.7 同时要求干扰物与障碍物不超阈值。这里没有将旧 pilot 的 10 mm 规定为正式数值。

当前正式 spec 已冻结 `non_task_position_m=0.003`；旧独立验收却对同一“相对 t0 的非目标移动”使用 `PROVISIONAL_RUNTIME_THRESHOLDS.non_target_displacement_m=0.010`。这是版本接线错误，不是两种能够互相替代的检查。新 `f1_verifier_contract` 把适用阶段写明为 **整个 N+1 状态序列相对 t0 的最大偏移**，按正式 3 mm 检查；rest、物体稳定和 release 的检查另列为退出后的稳定窗口。不是运行后取两者较小值，也不是根据旧轨迹拟合。

`contract_for_f1(spec)` 在运行前产生完整合同，正式 spec 将其纳入哈希；`frozen_contract` 要求合同存在且与对应字段一致。没有 provisional fallback。证据明确保留米、弧度、米/秒、弧度/秒、250 Hz、窗口帧数、参考帧和阶段。缺合同、采集器声明的合同与正式 spec 不同，均拒绝。

## 2. 真实抓持、释放与承重证据

`f1_disk_verifier.py` 直接读取原始 NPZ 与冻结 suffix artifact：

- identity 由 program 的 target role、原始 `audit_role_mapping`、实际抓持阶段的 selected-contact actor 和手指物理接触共同核对。修复了另一处接线问题：原 prefix 的辅助 `object_pose` 一直跟踪 red，不能拿它否定 green/blue；语义对象使用对应 `role_object_pose__<role>`。
- 开爪使用 **实际 measured master-joint qpos**，按冻结 `[-0.01, 0.045] m` 标定换算开度，沿用既有 0.8 开度要求。生产侧核对真实 robot 标定与合同一致；不以 `gripper_command` 证明开爪。
- 释放还要求稳定窗口内物体与所有机器人 link 没有物理接触。接触判定复用已有 v2 shape/point 证据与“非零冲量或非正 separation”定义。
- 承重要求真实 inside 几何、主体底面与接触点位于原 cavity 的支撑面高度带、接触法向以 world-z 分量为主、完整物理接触证据和稳定状态共同成立。仅 body pair 出现不能通过；睡眠状态下零冲量但非正 separation 的有效接触不会自动被判无支撑。
- 缺 shape、point normal/position 等证据属于数据合同问题；接触证据完整但真实放置、释放、稳定失败属于物理失败。

没有改动旧 raw、旧验收或旧接受历史。

## 3. 变体检查落在规定阶段

`native_f1.execute_with_stage_capture` 对原 F1 primitive 使用隔离的函数全局字典包装，只记录实际调用前后的 trace 行边界；不修改公共模块全局，也不重写抓法。记录包含 post-prefix hold、approach/grasp、gripper close、lift、carry、safe-horizontal、preplace/release、gripper open、release settle、retreat/rest 与 rest settle。

每个 arm segment 的实际 26-D effective setpoint 左臂 position/velocity 与对应冻结 control 数组逐段核对，同时检查阶段连续性、250 Hz、执行臂、非执行臂命令和规定 settle 时长。

- motion：额外帧必须在注册的 `post_prefix_hold`，帧数符合冻结规则、实际 effective/requested command 保持、实际 EEF 稳定；与 baseline 配对时，其余注册阶段的控制保持对应。不再使用“总长度变长”作为充分条件。
- path：冻结 safe-horizontal 目标必须等于其变换前目标加规定 y 偏移；与同意图 baseline 比较时，实际变化必须出现在这个运输段的端点，方向和既定最小差异要求正确。retreat 等无关阶段的偏离不能替代它。

## 4. 实际保存后立即独立检查

生产接口：

```python
finalize_native_cell(
    spec=resolved_spec,
    output=overall_root_output,
    program_id="F1-red",
    realization="r_pc",
    write_receipt=True,
)
```

只读重验为 `validate_saved_cell(spec, output, program_id, realization)`，或使用 `write_receipt=False`。

`native_f1_orchestrator` 在当前 cell 的 raw/trace/回执落盘、场景安全清理完成后调用此门，之后才允许下一个 branch。检查真实文件身份、raw contract、原始 RGB/state/anchor、row0 对齐、语义与阶段、实际磁盘到模型输入。首条不需要提前证明九格整体成立；跨分支 current/anchor、r_pc 共同前缀、realization 配对和完整矩阵仍由 root 检查。

失败产生 `failed_independent_cell` 并停后续 branch。`PHYSICAL_FAILURE` 只在 raw、身份、出口、阶段和信号完整，且失败仅为明确物理检查时产生；其余为 `DATA_CONTRACT_FAILURE`。runner pass 不替代独立门；runner 与独立结果不一致也不会自动接受。

首个通过的 cell 写出 `first_verified_cell.json`，绑定 raw、manifest、capture 及 SHA、spec/source bundle、独立 local receipt 路径与 SHA，供全族启动器重新核验后解锁第二 root。

## 5. 只读重验与显式源码兼容

`finalize_structure(..., write_receipt=False)` 重算 root 而不改写已存在的 root/cell 验收文件，供 copy-only 恢复使用。

九条数据的 anchor 比较仅使用各 raw 实际绑定的原始 capture，而不混入未作为数据使用的 qualification capture。原件均保留；物理等价使用共享版本化规则，文件复制完整性仍单独按 SHA。

普通源码修复必须通过明确的 source compatibility receipt、源文件与接受 cell 哈希、当前独立门重验。新旧真实 capture/anchor 原件保持各自实际 source 身份。为兼容继承的旧 artifact 比较器，另外记录 `source_comparison_view.json`：只把获准的 implementation source provenance 映射到原比较类并重算其依赖 hash，model-visible/hidden physical hashes、数值状态、物性和相机均不改。没有许可时仍严格拒绝；已批准后实际 prefix 数组、控制、root/program 和物理状态检查也不放宽。

## 6. CPU 验证与边界

定向反例经过真实保存和独立检查代码，包括：6 mm 非目标偏移；command open 但 measured qpos 未开；开爪后仍接触机器人；有 pair 却无物理承重；错误 rest；物体在盒子上方；轨迹更长但没有规定 hold；只有无关阶段 path 变化；缺正式合同。

实际 pipeline 测试证明：capture 写失败时 prefix/action 次数为零；第一条 raw 已保存但原图丢失时，独立门失败且 green/blue 不再执行；真实物理类型反例可与共享接口错误区分；root 只读重验不产生或修改 JSON；完整九格 fixture 的真实 disk finalizer、出口和独立副本链仍可运行。所有 fixture 均明确 synthetic，不能计入正式 90 条。

待真实首批检验的是新场景可达性、真实抓持/接触、原生相机行为以及时间/RSS；CPU 结果不声称这些已物理通过。动作与资格调用次数不因本次验收挂接增加，单条 CPU 检查如在 GPU lease 内运行，其实际用时仍照实计入 lease。

本实现者最终命令：

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/formal_entry_20260910 \
/nfs_share/lijunhui/Robotwin2/env/bin/python -m unittest \
  test_f1_verifier_cell test_family_entry -v
```

结果：19 项通过，34.963 秒。此为 CPU fixture 与真实保存/验收/副本接口测试；源码兼容 launcher 的完整恢复链由独立检查者另行复跑并出具记录，不用本结果替代它。

第二轮独立检查又直接复现了三个实际缺口：保存速度为零时窗口内 pose 仍可移动、EEF 只看最后一帧、非执行臂只看 position。已定向修复：subject 与 EEF 的线/角速度从原始 pose、wxyz quaternion 和 timestamps 重新差分；不要求底层 component velocity 的 measured 标志为 true，也不使用零值 fallback。新 F1 正式合同原已明确的最后 50 帧稳定 phase 同时用于 EEF rest 与速度，原 75 帧 rest_settle 控制及数值阈值不变；旧历史数据不倒判。非执行臂固定维度补全为右臂 position 6:12、velocity 18:24 和右夹爪 25。

最终补充命令使用 `test_independent_f1_verifier test_f1_verifier_cell test_family_entry`：31 次测试执行全通过，48.313 秒；其中独立模块导入复用了 8 条基类测试，实际为 23 个不同测试，不将重复执行当成新增覆盖。四个独立反例测试均通过。
