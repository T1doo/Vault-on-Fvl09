# F1–F4 implementation registry — runtime-v3_1 v5.1 current

当前状态：`a0_passed_f1_f4_terminal_blocked`；readiness=`BLOCKED_WITH_REASONS`。

| Component | Current version | CPU/code | 真实运行 |
|---|---|---|---|
| A0 monitor | `cmf_a0_activity_audit_v2` | native/wrapper/physics/timestep contracts；postmortem tests通过 | run3四场景pass |
| Authorization | `cmf_runtime_v3_1_gpu_authorization_v1_2` | parent request/source lock/≤1h/one-shot | run3新授权已消费，不可重放 |
| Guard | `cmf_gpu_guard_v2_2` | request/source/budget/GPU/PID binding | run3 pre/post安全通过 |
| Source lock | `cmf_runtime_source_lock_v1` | official/source/asset/config/env验证 | run3 launch通过 |
| Root | `real_sapien_pilot_root_orchestrator_v1_1` | freeze/task-physical/planner/raw/verifier/finalizer | 无accepted root |
| F1 | `f1_three_branch_coverage_v3_1` | task/physical 3/3、freeze once | planner terminal；2 repairs耗尽 |
| F2 | `f2_workspace_and_three_branch_v4_1` | same can/arm/relations | can无法full-OBB进入box strict cavity |
| F3 | `f3_release_and_full_program_v3_2` | pad与14段preflight通过 | prefix lift execution terminal；2 repairs耗尽 |
| F4 | `f4_common_carry_and_full_program_v3_2` | task/physical、Route1/2前4段通过 | center-high失败；无合规tray layout |
| Raw | `cmf_raw_attempt_v2_1_1` / layout v2_1 | 250Hz、26-D、N/N+1、hash contracts | family real raw未生成 |

A0 run1发现`is_sleeping` bool-property差异；run2证明sleep修复有效并成功保存pristine current/anchor，但被旧4ms exact-float validator拒绝，native planner ledger也尚未初始化。两次历史失败证据保持不变。

用户随后单独批准全新namespace下的一次postmortem-validation A0并通过。之后F1–F4有限nonformal scopes全部执行到各自停止线：F1/F3耗尽2轮repair仍失败，F2有固定asset/full-OBB物理不兼容，F4无合规tray impact candidate且末次postcheck遭外部GPU进程占用。Accepted real root=0，Stage0三份准备包未生成，readiness继续`BLOCKED_WITH_REASONS`。完整机器字段、代码hash和evidence路径见同名JSON。
