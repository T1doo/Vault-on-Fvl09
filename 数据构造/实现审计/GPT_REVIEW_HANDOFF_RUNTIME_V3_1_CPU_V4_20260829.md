# GPT 审阅入口：runtime-v3_1 CPU hardening v4

## 定位

- Repository：`https://github.com/T1doo/Vault-on-Fvl09`
- Branch：`main`
- 本轮 content commit：`PENDING_CONTENT_COMMIT`
- Design：`controlled_multi_future_f1_f4_v1_2`
- Implementation：`controlled_multi_future_runtime_v3_1`
- Revision：`runtime_v3_1_cpu_hardening_v4`
- 当前裁决：`BLOCKED_WITH_REASONS`
- `gpu_probe_authorized=false`
- `stage0_authorized=false`

本文件 supersede CPU V3 handoff 作为 current review 入口。V1–V3 handoffs 和 cpu1–cpu7 均保留为历史。本轮没有运行 GPU、A0、SAPIEN scene 或 action probe。

## 阅读顺序

1. `Idea/项目核心Idea.md`
2. `数据构造/数据构造方案.md`
3. 本文件
4. `数据构造/实现审计/controlled_multi_future_runtime_v3_1_implementation_proposal.md/json`
5. `数据构造/实现审计/pilot_attempt_budget_runtime_v3_1_proposal.md/json`
6. `数据构造/实现审计/f1_f4_implementation_registry_v3_1_cpu_current.md/json`
7. `数据构造/实现审计/stage0_readiness_report_runtime_v3_1_current.md/json`
8. `数据构造/实现审计/runtime_v3_1_cpu_static_audit_v4_20260829.json`
9. `数据构造/正式数据构造日志.md` 最新章节
10. `数据构造/实现审计/代码审阅快照/`

## V4 相比 V3 的唯一实现主题：A0 变成独立、可测试的零动作 Gate

上一版已完成 root/family/raw/current/anchor/GPU guard/F3 conditional correction 的 CPU 加固。本版没有改变这些语义，也没有扩展 family action scope；只补齐真实 GPU 前的最后一个 CPU 结构缺口：原先 A0 四场景逻辑直接写在 GPU CLI 中，无法在不初始化 SAPIEN/GPU 时独立反证。

新增：

```text
controlled_multi_future/a0_orchestrator_v1_1.py
└── A0CurrentAnchorOrchestratorV1_1
```

固定流程：

```text
A0_pristine
→ capture reference current + physical anchor + activity audit
→ unique scene-bound cleanup
→ A0_fresh_1
→ same-current + anchor equivalence + zero activity + cleanup
→ A0_fresh_2
→ same checks
→ A0_fresh_3
→ same checks
→ passed_nonformal_A0
```

每个 scene 必须有唯一 `scene_instance_id`，并显式证明：

```yaml
planner_query_count: 0
planner_query_record_count: 0
action_execution_count: 0
canonical_settle_is_control_action: false
```

Canonical scene setup 的 60 个物理 settle steps 单独记录，不冒充 controlled action。以下任一情况立即终止，不继续后续 scene：

- fresh current mismatch；
- physical anchor mismatch；
- planned root spec mutation；
- missing/reused/uncertain cleanup receipt；
- orphan count 非 0；
- 任一 planner query 或 controlled action；
- adapter 缺少 structured activity audit。

真实 A0 CLI 现在只做：

```text
content-hashed user authorization
→ atomic fresh-idle GPU guard
→ CUDA UUID/index binding
→ concrete real adapter
→ A0 orchestrator
→ top-level receipt for guard postcheck
```

它仍然无法在没有独立授权 receipt 时运行。

## 新增测试

`tests/controlled_multi_future/test_a0_orchestrator_v1_1.py` 包含 5 项：

1. 1 pristine + 3 fresh 全部 same-current/anchor、zero planner/action、cleanup 通过；
2. `A0_fresh_2` current mismatch 后终止，不开 fresh3；
3. anchor mismatch 后终止；
4. cleanup uncertainty 后终止；
5. 任一 planner activity 触发 `failed_zero_action_contract`。

第一次目标测试调用使用了错误的 unittest module path，产生 1 次 loader error；改用仓库标准 discovery 后 5/5 通过。该失败是测试命令错误，不是实现行为失败，未隐去。

## Current CPU evidence

- Active tests：88/88 passed；
- Vault byte-equal snapshot：88/88 passed；
- 61 Python files compile passed；
- Registry current code hashes：24/24 active/snapshot matched；
- Current root evidence：`数据构造/实现审计/probe_outputs/nonformal_root_pipeline_dry_run_runtime_v3_1_20260829_cpu8/`；
- Root receipt SHA-256：`465f7af2467d28f1d6348a802422f1b155aa1e6888b744bc78225399eb207829`；
- synthetic status=accepted、cleanup=10/10、raw integrity=3/3、prefix hash count=1、first suffix hash count=3、divergence step=2。

Cpu8 是 root pipeline synthetic evidence，不是 A0/SAPIEN/GPU evidence。A0 的 current evidence目前只有 5 项 adapter-agnostic CPU tests。

## 仍未完成

1. A0 real-SAPIEN smoke 未运行；
2. 所有 concrete adapter/runner 仍无 runtime-v3_1 真实 GPU evidence；
3. F1 real 3/3、F2 beside、F3 diagnosis/correction、F4 common-X routes 均未运行；
4. F3 完整 VVHH/VHVH/VHHV 和 F4 A/B/C、ABC/ACB/BAC 仍 deliberate incomplete/fail-closed；
5. Budget 未批准、未冻结；不存在 GPU authorization receipt；
6. Stage 0/1/formal trajectory count 均为 0，`H_reveal=null`，无 training/compression/π0.5。

## 请 GPT 裁决

1. A0 核心从 GPU CLI 抽成 adapter-agnostic orchestrator 后，四场景、same-current/anchor、zero planner/action、scene-bound cleanup 的 fail-closed 结构是否充分？
2. `capture_a0_activity_audit()` 对 planner query records、trace rows、setup settling 与 controlled action 的区分，是否还有必须在真实 GPU 前补的 P0？
3. A0 receipt 的失败分类与终止线是否充分？
4. 在继续保持 budget `approved=false / frozen=false` 的前提下，是否可以进入“用户单独批准 A0”的决策？
5. 即使未来批准 A0，也不要自动批准 family action probes或 Stage 0。

请勿把 CPU/synthetic pass解释成真实 SAPIEN 可行性，也不要批准 Stage 0。
