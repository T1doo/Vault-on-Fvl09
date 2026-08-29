# F1–F4 implementation registry — runtime-v3_1 v5.1 current

当前状态：`a0_passed_family_runtime_not_run`；readiness=`BLOCKED_WITH_REASONS`。

| Component | Current version | CPU/code | 真实运行 |
|---|---|---|---|
| A0 monitor | `cmf_a0_activity_audit_v2` | native/wrapper/physics/timestep contracts；postmortem tests通过 | run3四场景pass |
| Authorization | `cmf_runtime_v3_1_gpu_authorization_v1_2` | parent request/source lock/≤1h/one-shot | run3新授权已消费，不可重放 |
| Guard | `cmf_gpu_guard_v2_2` | request/source/budget/GPU/PID binding | run3 pre/post安全通过 |
| Source lock | `cmf_runtime_source_lock_v1` | official/source/asset/config/env验证 | run3 launch通过 |
| Root | `real_sapien_pilot_root_orchestrator_v1_1` | freeze/task-physical/planner/raw/verifier/finalizer | 未运行 |
| F1 | `f1_three_branch_coverage_v3_1` | red/green/blue与actual-prefix代码就绪 | 未运行；historical仅red通过 |
| F2 | `f2_workspace_and_three_branch_v4_1` | six-pose/chained/full-root代码就绪 | 未运行；historical beside失败 |
| F3 | `f3_release_and_full_program_v3_2` | diagnosis/conditional repair + 3 full programs | 未运行；historical return失败 |
| F4 | `f4_common_carry_and_full_program_v3_2` | common route + 3 full programs/block verifier | 未运行；historical common-X失败 |
| Raw | `cmf_raw_attempt_v2_1_1` / layout v2_1 | 250Hz、26-D、N/N+1、hash contracts | family real raw未生成 |

A0 run1发现`is_sleeping` bool-property差异；run2证明sleep修复有效并成功保存pristine current/anchor，但被旧4ms exact-float validator拒绝，native planner ledger也尚未初始化。两次历史失败证据保持不变。

用户随后单独批准全新namespace下的一次postmortem-validation A0。Run3在GPU0完成四个唯一scene：current hash和physical anchor hash分别四场一致，planner/control/post-setup physics全部为0，cleanup与GPU release通过，orphan=0，16/16引用artifact独立重哈希通过。因此A0 Gate现在为pass；但F1–F4和真实root尚未执行，Stage 0仍为`BLOCKED_WITH_REASONS`。完整机器字段、代码hash和evidence路径见同名JSON。
