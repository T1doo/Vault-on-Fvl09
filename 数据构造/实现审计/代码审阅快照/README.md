# F1–F4 additive 代码审阅快照

该目录是 active RoboTwin additive source 的 byte-equal 审阅副本，供外部 GPT 通过 GitHub 只读审阅。

- active source：`/nfs_share/lijunhui/Robotwin2/project/RoboTwin/controlled_multi_future/`
- active tests：`/nfs_share/lijunhui/Robotwin2/project/RoboTwin/tests/controlled_multi_future/`
- official baseline：`c3ddfa8b97d5519efa828b075999bd0006778e5e`
- 科学设计：`controlled_multi_future_f1_f4_v1_2`
- 当前实现：`controlled_multi_future_runtime_v3_4`
- 当前策略：`diagnosis_first_multi_gpu_convergence`
- 当前状态：Revision-9三份离线forensics与v3_4 CPU/source freeze完成；F1 revision-2仍是唯一accepted nonformal root。因共享root-orchestrator/planner-audit/Guard接线变化，F1需一次shared regression；F2/F3/F4 targeted Gate与完整root尚未运行；accepted roots=1/4；Stage 0未授权。
- 2026-08-30 active 与本快照各 `449/449 tests passed`，两棵 source/test 目录 `diff -qr` 无差异，source SHA=`1cadd3e28af56f56c32e8fe363fbeb3c2f3397ff196a63c6bd115285aa85b316`，tests SHA=`c17bb067fa6a304ba0ca2e55fbee9772540ea3516a4f45367486af72db561eb8`。

本快照不是 active source，不得从这里运行 GPU、Stage 0 或 formal collection。所有实现修改必须先发生在 active RoboTwin additive source，验证后再同步。

## runtime-v3_3 主要入口

- `canonical_prefix_artifact_v1.py`：封存一次规划得到的 26-D/250 Hz canonical prefix、requested/mask、左右gripper底层joint drive target/velocity、reference trace、physical-acceptance 和 semantic/settling 边界。
- `canonical_prefix_replay_v1.py`：fresh scene 中逐 step 重放完全相同的 effective-setpoint bytes，并复核 requested/mask/current/anchor/end state；不调用 planner。
- `frozen_suffix_artifact_v1.py`：把实际 replay-end qpos 后规划出的 suffix control arrays、planner receipts、目标与链式 qpos 封成不可变 artifact。
- `root_orchestrator_v1_2.py`：pristine→3 task/physical scenes→freeze once→prefix once→3 suffix preflights→3 fresh executions→3/3 finalizer。
- `real_sapien_adapter_v1_3.py`、`family_runners_v3_3.py`：真实 SAPIEN strict-prefix adapter 与 F1–F4 family controllers。
- `canonical_prefix_smoke_v1.py`：一次 prefix generation 加三 fresh exact replays 的非正式架构 smoke。
- `f4_cube_grasp_ik_audit_v1.py`：A/B/C procedural cube 的 right-arm no-action/IK Gate。
- `f4_staged_block_gate_v1.py`：`A-only → B-only → C-only → A+B noninterference`，通过后才允许 F4 full root。
- `runtime_v3_3_budget_v1.py`：与 Vault GPU0–7 budget v1.1 JSON逐字段一致，hash=`68cee0949ccb6d87bef5255560bf32737d0d79dc803dfd92ac71d1098cad5d2c`。
- `pre_stage0_authorization_v3.py`、`probes/runtime_v3_3_authorization_v1.py`：parent/request/source/code/budget/family/seed/spec/output/command one-shot binding，以及每 family 最多两个 source-distinct revisions 的 canonical ledger。
- `probes/gpu_guard_v2_4.py`：GPU0–7 single-card Guard；每卡原子lease、双fresh-idle/UUID检查、job-local HOME/cache/TMP、PID/PGID与信号清理、post source-lock和release audit。
- `probes/runtime_v3_3_scope_runner.py`：唯一 current GPU child entrypoint；始终 `formal_data=false/stage0_data=false/stage0_authorized=false`。
- `runtime_v3_3_scope_specs_v1.py`、`runtime_v3_3_scope_bundle_v1.py`：冻结 planned specs 与 CPU-only request/source-lock/authorization bundle builder。

## runtime-v3_4 diagnosis-first 入口

- `runtime_v3_4_forensics.py`：从immutable Revision-9 raw生成F2 timeseries、F3 r8/r9 causal diff与F4 carry-pose comparison。
- `f2_release_gates_v10.py`：release-safety与final-inside success分账；最终阈值不放宽。
- `f3_grasp_robustness_v10.py`、`f3_grasp_three_context_gate_v10.py`：统一contact0/candidate0中段侧抓与三上下文pre-release Gate。
- `f4_carry_corridor_v10.py`、`f4_corridor_selection_gate_v10.py`、`f4_corridor_a_gate_v10.py`、`f4_bc_ab_gate_v10.py`：fixed-order corridor与A→B/C/AB staircase。
- `runtime_v3_4_budget_v1.py`、`runtime_v3_4_scope_specs_v1.py`、`runtime_v3_4_scope_bundle_v1.py`：GPU0–7有限scope、前置Gate与single-use bundle。
- `runtime_v3_4_multi_gpu_scheduler_v1.py`：family-level parallel、一卡一job、root不shard。
- `probes/runtime_v3_4_authorization_v1.py`、`probes/runtime_v3_4_scope_runner.py`：source/request/budget/UUID绑定与唯一child入口。

## Family 当前 CPU 修复

- F1：revision-2已accepted；同一planner-assisted top-down + 4 cm + 4 cm lift，统一frozen cluster-center carry hub；三分支3/3。
- F2：dynamic can只在task/physical执行post-settle pose/contact/upright Gate；held suffix不再错误套spawn Gate。
- F3：V/H固定7-target闭环与每endpoint 50-frame hold；pose-derived linear+angular Gate，component velocity仅audit。
- F4：common-X与A/B/C共享显式right-arm cube grasp contract；common9+每block6结构硬校验。
- F2：固定同一 `071_can/base1`、left arm、official plasticbox/base2；联合布局 v2 的 inside/on/beside 区域经 5 mm 网格证明互斥；beside z 由冻结桌面支撑高度决定；inside 保存 release 前后动态样本且 full-OBB verifier 不放宽。
- F3：prefix 固定 grasp/lift/central/shared-first-V；reference 和每次 replay 都硬检 realized EEF/bottle V、off-axis/return、速度、selected contact 与 grasp-transform drift。
- F4：同一显式 right-arm cube grasp generator用于 A/B/C；每 block 检查指定夹爪接触、连续稳定 slot completion、table support、non-target/prior-slot/common-X preservation 和 neutral boundary。

## 验证命令

在本快照目录执行：

```bash
PYTHONPATH=/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/代码审阅快照 \
PYTHONDONTWRITEBYTECODE=1 \
  /nfs_share/lijunhui/Robotwin2/env/bin/python \
  -m unittest discover \
  -s tests/controlled_multi_future \
  -p 'test_*.py' -v
```

真实 probe receipts、NPZ、guards 和 source locks 不复制进代码快照，统一保存在相邻审计目录。历史证据保持其原source/GPU0 authorization；任何后续 evidence 都必须经当前published HEAD、fresh source-lock、GPU0–7 parent authorization与one-shot Guard产生。

## Current GPU parallel policy v2

- `gpu_parallel_policy_v2.py`：面向后续新job的GPU0–7机器策略与动态partial-wave scheduler；一张空闲即调度一个，多张空闲并行多个；一卡一job、root不shard、无GPU0 fallback。
- 历史`stage0_smoke_parallel_scheduler_v1/v1_1`及GPU0-only authorization保持不可变，只解释原执行，不再作为新batch模板。
- 新job在scheduler assignment后仍必须由`gpu_guard_v2_4.py`即时重新检查fresh-idle/UUID并取得per-GPU lease；scheduler不保留GPU、不消费authorization。
