# GPT 审阅入口：runtime-v3_1 CPU hardening v2

## 定位

- Repository：`https://github.com/T1doo/Vault-on-Fvl09`
- Branch：`main`
- 本轮 content commit：`207d566fa67b61de23142baa4b1d1be552d58924`
- Design：`controlled_multi_future_f1_f4_v1_2`
- Implementation：`controlled_multi_future_runtime_v3_1`
- Revision：`runtime_v3_1_cpu_hardening_v2`
- 当前裁决：`BLOCKED_WITH_REASONS`
- `gpu_probe_authorized=false`
- `stage0_authorized=false`

本文件 supersede `GPT_REVIEW_HANDOFF_RUNTIME_V3_1_CPU_20260829.md` 作为 current CPU review 入口；旧文件和 cpu1–cpu5 均保留为历史。本轮仍未运行 GPU、A0、真实 SAPIEN scene 或 action probe。

## 阅读顺序

1. `Idea/项目核心Idea.md`
2. `数据构造/数据构造方案.md`
3. 本文件
4. `数据构造/实现审计/controlled_multi_future_runtime_v3_1_implementation_proposal.md/json`
5. `数据构造/实现审计/pilot_attempt_budget_runtime_v3_1_proposal.md/json`
6. `数据构造/实现审计/f1_f4_implementation_registry_v3_1_cpu_current.md/json`
7. `数据构造/实现审计/stage0_readiness_report_runtime_v3_1_current.md/json`
8. `数据构造/实现审计/runtime_v3_1_cpu_static_audit_v2_20260829.json`
9. `数据构造/正式数据构造日志.md` 的最新 runtime-v3_1 章节
10. `数据构造/实现审计/代码审阅快照/`

## 相比上一份 handoff 新增的实质加固

### F1 prefix 与 root finalizer

- F1 rollout 在实际 prefix 结束前不读取 `program[target_role]` 或 target-specific execution spec；prefix 使用固定 audit actor、固定 neutral 公式与固定 planner reset；
- target role 只在 prefix end anchor 保存后读取；contact subject 在边界后切换，固定 `object_pose` audit identity 不变，所有角色另存 `role_object_pose__*`；
- root orchestrator 从 raw `controller_effective_setpoint` 重算 prefix action hash和逐 step suffix hashes，不信任 adapter 自报；
- finalizer 横向计算真正 `first_post_prefix_divergence_step`；三条 suffix 从不分叉会失败；cpu6 证明 prefix hash count=1、首个 suffix hash count=3、divergence step=2。

### Family verifier 与 planner chain

- F1：非目标物体从 prefix 前 baseline 开始做分阶段 displacement，加入 support/stability/gripper/rest/EEF stationarity；
- F2：task/physical 层增加 can-box fit、scale functional point 和 beside targets clearance；planner terminal 6-D arm qpos 合并回完整 articulation qpos；actual rollout再保存真实 preplace→release full-qpos chain，并把 support/rest/stationarity 纳入 verifier；
- F3：task/physical scene 做 50-frame pad contact/footprint/速度稳定窗口；release samples 强制 linear/angular speed、pad contact normals/impulse、selected-gripper contact、actual gripper qpos；最终 pass 加入 rest/gripper/EEF stationarity；
- F4：task/physical 层检查 tray/slot/object geometry；common-X verifier加入 A/B/C staged noninterference、neutral/rest/gripper/EEF stationarity；gripper envelope由 selected left-gripper link runtime poses + frozen margin推导，不再硬编码。

F3 仍只覆盖 V→H repair diagnosis，F4 仍只覆盖 common-X repair；完整 programs 继续明确 fail-closed。

### Current/anchor 与 provenance

- `current_context_hash_v2.aggregate_sha256` 现在只锁 model-visible current + reconstruction spec；
- hidden actor pose/velocity 不再做错误的 bitwise same-current Gate，而由 `physical_anchor_v2` position/orientation/velocity/sleep tolerance 比较；
- 每实体 asset hash、body/mass/friction/collision registry、simulation config、official commit 与 additive implementation aggregate source hash 都进入 anchor/reconstruction evidence；
- real `trace_source.npz` 在可用时独立保存并从 manifest 相对路径重哈希；manifest payload hash 会真正重算，sidecar 自身 hash 进入 branch receipt。

### Atomic GPU guard

- Guard 在 child launch 前落 `precheck_passed` receipt；child 必须匹配 guard parent PID、physical index、UUID，且 precheck age≤60秒、P8、≤100 MiB、≤1% util、无 compute process；
- A0/root/family child 均写顶层 `receipt.json`，供 guard 原子写入 postcheck；
- scene/planner orphan 与外层 process-group orphan 分开保存后合计，任何一侧非零都 `failed_cleanup_uncertain`；
- 没有内容哈希授权 receipt 或 atomic guard 环境，真实 CLI 在创建 scene 前拒绝运行。

## CPU evidence

- Active tests：79/79 passed；
- Vault byte-equal snapshot tests：79/79 passed；
- 57 Python files compile passed；
- Current namespace：`数据构造/实现审计/probe_outputs/nonformal_root_pipeline_dry_run_runtime_v3_1_20260829_cpu6/`；
- Root receipt SHA-256：`6aca38c2f49f8fad59834e45c6aad47dc3da7db0535b63af2d321d520dea8bcb`；
- status=accepted synthetic-only、freeze=1、task/physical=3、planner=3、rollout=3、cleanup=10/10、raw integrity=3/3；
- prefix action hash count=1、first suffix action hash count=3、computed divergence step=2；
- 全部 `formal_data=false`、`stage0_data=false`、`synthetic=true`。

## 仍未完成

1. A0 real-SAPIEN zero-action smoke 未运行；
2. concrete adapter/runner 没有真实 runtime evidence；
3. F1 real red/green/blue 3/3 未运行；
4. F2 real beside 未运行；
5. F3 real V→H release diagnosis 未运行，完整三个 programs incomplete；
6. F4 real common-X routes 未运行，A/B/C 与三个完整 programs incomplete；
7. Budget 仍 proposed/unapproved/unfrozen；
8. Stage 0 仍禁止。

## 请 GPT 裁决

1. 上述 hardening v2 是否解决上一轮剩余的 GPU 前 P0？
2. F1 target-neutral prefix 与 raw-derived divergence 证据是否充分？
3. same-current exact hash + physical-anchor semantic equivalence 的职责分层是否正确？
4. trace/manifest sidecar integrity 与 atomic GPU guard绑定是否充分？
5. 是否可以只批准 A0：0 planner query、0 action、1 pristine+3 fresh scenes、600秒；仍不批准 family actions？
6. 若 A0 通过，当前 finite family envelopes 是否可继续逐 Gate 审批？
7. 是否同意继续 `BLOCKED_WITH_REASONS` 并禁止 Stage 0？

请勿把 CPU/synthetic pass解释成真实 SAPIEN 可行性。
