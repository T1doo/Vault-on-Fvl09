# GPT 审阅入口：runtime-v3_1 CPU hardening v5

## 定位

- Repository：`https://github.com/T1doo/Vault-on-Fvl09`
- Branch：`main`
- V5 code/test snapshot content commit：`3e7cba9e1dc798f9e18a1c23e4811c80f664bf1a`
- Design：`controlled_multi_future_f1_f4_v1_2`
- Implementation：`controlled_multi_future_runtime_v3_1`
- Revision：`runtime_v3_1_cpu_hardening_v5`
- Stage-0 decision：`BLOCKED_WITH_REASONS`
- A0 readiness：`READY_FOR_USER_REVIEW_BEFORE_A0`
- `gpu_probe_authorized=false`
- `stage0_authorized=false`

本文件 supersede CPU V4 handoff 作为 current review 入口。V1–V4 handoffs、cpu1–cpu9 与所有历史失败均保留。本轮没有运行 GPU、SAPIEN scene、真实 A0 或 family action probe。

## 阅读顺序

1. `Idea/项目核心Idea.md`
2. `数据构造/数据构造方案.md`
3. 本文件
4. `数据构造/实现审计/A0_USER_APPROVAL_REQUEST_RUNTIME_V3_1_V5.md/json`
5. `数据构造/实现审计/a0_post_setup_activity_entrypoint_registry_v2.md/json`
6. `数据构造/实现审计/controlled_multi_future_runtime_v3_1_implementation_proposal.md/json`
7. `数据构造/实现审计/pilot_attempt_budget_runtime_v3_1_proposal.md/json`
8. `数据构造/实现审计/f1_f4_implementation_registry_v3_1_cpu_current.md/json`
9. `数据构造/实现审计/stage0_readiness_report_runtime_v3_1_current.md/json`
10. `数据构造/实现审计/runtime_v3_1_cpu_static_audit_v5_20260829.json`
11. `数据构造/正式数据构造日志.md` 最新章节
12. `数据构造/实现审计/代码审阅快照/`

## 本轮一次性完成的 CPU/code 工作包

### 1. 真正独立的 post-setup activity monitor

新增：

```text
controlled_multi_future/a0_activity_monitor_v2.py
```

生命周期现在明确分为：

```text
setup_demo
  包含 homestate、initial gripper、check_stable 与官方初始化活动
→ 60 × canonical scene.step settle
  只作场景稳定
→ monitor_start
→ current/anchor capture
→ monitor_stop
→ instrumentation restore
→ scene cleanup
```

A0 的0 action只指 post-setup monitored window，不再声称从scene创建开始没有动作。

Monitor 不依赖 trace 证明0 action。它以 instance-local wrappers/proxy 覆盖：

- Base_Task task control、move、grasp/place、gripper、take_dense_action/take_action；
- Robot path/batch/gripper planners和planner wrappers；
- Robot direct arm/gripper drive setters；
- renderer-only update；
- `task.scene.step` physics call。

`trace_row_delta=null` 只表示trace未初始化，不能自动推导action=0。独立counter/record必须全部为0。

Schema：`cmf_a0_activity_audit_v2`。Receipt绑定scene ID、phase、monitor boundary、setup summary、独立deltas、entry-point registry hash、install/restore、limits和内容hash。任何缺失、重用、旧schema、binding错误或nonzero activity都terminal。

### 2. A0 orchestrator v1_2

新增：

```text
controlled_multi_future/a0_orchestrator_v1_2.py
```

固定：`A0_pristine → A0_fresh_1 → A0_fresh_2 → A0_fresh_3`。

每scene分离保存：

```text
current.json
anchor.json
activity.json
cleanup.json
artifact_hashes.json
```

Top receipt只引用hash。Current/anchor mismatch保存component-level diagnostics，但diagnostics不放宽严格Gate。Failure statuses区分current、anchor、cleanup、candidate mutation、monitor installation/restoration、activity unbound/reuse/nonzero和summary invariant。

### 3. Real adapter/context v1_2

新增：

```text
RoboTwinRealSapienPilotRootAdapterV1_2
RoboTwinSceneContextV1_2
```

- import仍不加载SAPIEN/Torch/CUDA；scene class只在context entry内lazy import；
- monitor只在setup+60 settle后安装；capture完成后停止；cleanup再次保证restoration；
- A0验证真实timestep=0.004、control_steps_per_action=1；
- camera resolution/intrinsics/extrinsics/mount来自runtime API，near/far/render settings明确标记declared_config来源；
- project RGB block/pad/marker/slot的half-size、color、collision/visual-only、material source与creation API/version进入hash；
- friction和mass明确保存value+source，不把统一0.5冒充per-actor实测。

### 4. One-shot authorization v1_1

新增：

```text
cmf_runtime_v3_1_gpu_authorization_v1_1
controlled_multi_future/probes/runtime_v3_1_authorization_v1_1.py
```

Authorization绑定：scope、family、seed、planned spec/hash、content/source hashes、budget、timeout、max invocation、output、child command、allowed GPU index/UUID policy、issued/expires。

Guard fresh-idle通过后、child launch前，以`O_CREAT|O_EXCL`创建consumption receipt。第二次使用同authorization必失败；首次child后续失败也不返还授权。

本轮没有生成approved receipt。待审批request内template仍为：

```yaml
approved: false
issued_at: null
expires_at: null
receipt_sha256: null
```

### 5. GPU Guard v2_1

新增：`cmf_gpu_guard_v2_1`。

Guard/child双向核对authorization ID/hash、consumption、scope、family、seed/spec、implementation/budget hash、timeout、output、command、physical index/UUID、parent PID和≤60秒fresh-idle precheck。仍负责独立process group、600秒timeout、child receipt、orphan cleanup和post-release。

### 6. 通用未来scope预算基础

新增：`cmf_runtime_v3_1_scope_budget_v1_1`，覆盖：

```text
A0_current_anchor_smoke
F1_three_branch_nonformal_probe
F2_beside_nonformal_probe
F3_release_diagnosis_nonformal_probe
F4_common_carry_nonformal_probe
real_sapien_root_integration_nonformal_probe
```

只有A0 `currently_requestable=true`。Root/family current CLIs已使用new authorization/guard/adapter/budget validator，但没有对应approved receipt，不能运行。历史runtime-v2/scene-inspection/environment-certification/guard CLIs已显式disabled；旧纯函数与证据仍保留。

## A0待审批请求

```text
数据构造/实现审计/A0_USER_APPROVAL_REQUEST_RUNTIME_V3_1_V5.md
数据构造/实现审计/A0_USER_APPROVAL_REQUEST_RUNTIME_V3_1_V5.json
```

固定请求：F1、seed 20260829、1 pristine + 3 fresh、post-setup planner/control/physics=0、600秒、max_invocations=1。

```yaml
approval_request_sha256: 0e845b6f694a696b8a21f56f00590679e90e0fefd3de126d8b9675c0646baade
implementation_source_sha256: 1aace10635af7d4aa1c371ac0818249081a83d55623871eaf5346b3af2810ab0
a0_orchestrator_sha256: bbcb7521581886b7520a075a7846eba15cf5d7373f3a318ac43768b6e7eb8a1f
a0_activity_monitor_sha256: aaf4c6399bddf3b13ef9bacddda9dfbb22a7ed0baffb50154e614852f99e7154
real_adapter_sha256: 5b7493ada5c9a6b838d3257fe1dde5a00fb637a539513e89a007387df30ff0eb
gpu_guard_sha256: 27e8468121c3d213bf3cea7c44e7beebee02f0890244d4462eb509fb5deecced
budget_receipt_sha256: c793faf2f3017fbd1b9b52dc4a7f71262ff5fa73ae2286f7873691f9101d1cd0
```

## 测试与机器证据

- active：131/131 passed；
- byte-equal Vault snapshot：131/131 passed；
- Python compile：76 files passed；
- current registry：35/35 active/snapshot hashes matched；
- import-side-effect：新增V5 modules未加载`sapien`、`torch`或CUDA；
- authorization replay/activity monitor/guard binding tests均通过；
- current root regression：`probe_outputs/nonformal_root_pipeline_dry_run_runtime_v3_1_20260829_cpu10/`；
- cpu10 root receipt SHA：`29462ada71ee014d81f75e0682115f54b4b690db74f3d8a179762f925d9e6f8a`；
- cpu10 synthetic accepted、cleanup10/10、raw integrity3/3、prefix hash count1、first suffix hash count3、divergence step2。

### 保留的一次测试失败

首次同步V5 snapshot后，snapshot suite出现2个import errors：v1_2 adapter在module import时按snapshot相对路径读取`envs/utils/create_actor.py`。Active有官方env，snapshot没有。修复为固定commit下已审计的official source hash常量，不再import-time读取外部env路径；之后active/snapshot均131/131。cpu9保留，修复后生成cpu10作为current。

## 当前边界

```text
Stage-0 decision = BLOCKED_WITH_REASONS
a0_user_approval_readiness = READY_FOR_USER_REVIEW_BEFORE_A0
A0 request approved = false
real A0 count = 0
Stage 0/1/formal count = 0
H_reveal = null
```

F1/F2/F3/F4真实repair/full-program blockers没有被CPU pass改写；F3完整VVHH/VHVH/VHHV和F4 A/B/C、ABC/ACB/BAC仍未运行。无training/compression/π0.5。

## 请GPT裁决

1. Post-setup monitor的入口覆盖、trace-independent counter和setup/settle边界是否足以提交用户批准？
2. Activity/cleanup/handle identity、receipt one-use、wrapper restoration与per-scene artifacts是否还有CPU P0？
3. Authorization v1_1的family/seed/spec/source/budget/output/command/expiry/one-shot binding是否充分？
4. Guard v2_1是否充分防止timeout/output/hash/GPU/PID不一致和authorization replay？
5. Adapter的camera/procedural asset/friction source语义是否准确？
6. 若无CPU blocker，请明确确认可以由用户单独决定是否批准一次A0；不要批准family probes或Stage0。

请勿把CPU/synthetic结果解释成真实SAPIEN证据。
