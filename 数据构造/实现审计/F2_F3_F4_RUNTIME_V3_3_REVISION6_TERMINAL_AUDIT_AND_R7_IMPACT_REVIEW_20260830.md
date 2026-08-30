# runtime-v3_3 revision-6 终止审计与 revision-7 impact review

## 裁决

`BLOCKED_WITH_REASONS`。F1仍是唯一accepted nonformal pre-Stage-0 root；F2、F3、F4 revision-6均留下完整或明确标注缺口的终止证据，不计入Stage 0或正式分母。

## F2

`on`与`beside` accepted；`inside`的r6 `10 warmup + final50`和完整60帧安全Gate通过，但strict full-OBB inside失败。开夹前EEF/actor相对目标已有约`11.8 mm / 92.8 mrad`系统偏差，而抓取变换仅漂移`0.122 mm / 0.018 mrad`；开夹过程中罐头仍被手指带着高速旋转，最终卡在盒外。下一版只允许inside-only确定性tracking compensation与开夹前realized alignment Gate，不改物体、臂、盒子、布局、desired actor target或verifier。

## F3

三个program都没有进入suffix planner。Runner读取旧键`gripper_below_eef_envelope_m`，而r6 helper返回`gripper_assembly_below_eef_m`，因此一致触发`KeyError`；21次planner全属于成功的canonical prefix，suffix=0、execution=0。r6 10 mm release clearance没有被真实测试。下一版修复单一接线错误，并补consumer integration test、pre-planner partial evidence和implementation-error分类。

## F4 micro

+16 mm修复使pregrasp/grasp边界、open-before-close、双指contact、noninterference和forbidden-nonzero-contact全部通过。当前verifier却把primary `actor_pose`（仍为common-X）当作A；role-specific raw显示A实际上升`17.3066 mm`，已超过15 mm门槛。尾10帧A-table pair的impulse均精确为0，属于speculative pair，但旧Gate仅按pair presence判接触。该run不能retroactive accept；下一版必须使用`role_actor_poses['A']`并按同一Gate既有nonzero-impulse语义判断物理接触，再fresh rerun A-only micro。

F4 Guard结束时GPU0被一个工作区外部、非本任务Python进程占用，immutable Guard因此保持`failed_cleanup_uncertain`。本任务child/PGID为`2628816`，scene cleanup成功、task-owned orphan=0；未杀死或干预外部PID，随后停止GPU0后续运行。

## 机器证据

| Family | Files | Evidence tree SHA-256 |
|---|---:|---|
| F2 | 42 | `3e23874fc20c7fa7bacaa2d5ed3ce84e9d13fd4c53415671863b06809f2ec487` |
| F3 | 18 | `ddd478898170cc300c3bb5af291f1afb766bee2ed9ab89d815ccca2f351e831a` |
| F4 micro | 17 | `54394267f603febc78359d456877fcd7ea47f9fc76ea0659831acdd622afc842` |

Revision-7仍必须是新source hash、immutable namespace、finite one-shot budget、automatic retry=false、recovery=0。Stage0继续禁止。
