# GPT 审阅入口：runtime-v3_1 CPU hardening v3

## 定位

- Repository：`https://github.com/T1doo/Vault-on-Fvl09`
- Branch：`main`
- 本轮 content commit：`0c74faae237430d931c16e1c08e2913e100d22c5`
- Design：`controlled_multi_future_f1_f4_v1_2`
- Implementation：`controlled_multi_future_runtime_v3_1`
- Revision：`runtime_v3_1_cpu_hardening_v3`
- 当前裁决：`BLOCKED_WITH_REASONS`
- `gpu_probe_authorized=false`
- `stage0_authorized=false`

本文件 supersede CPU V2 handoff 作为 current review 入口。V1/V2 handoffs 和 cpu1–cpu6 均保留为历史。本轮没有运行 GPU、A0、SAPIEN scene 或 action probe。

## 阅读顺序

1. `Idea/项目核心Idea.md`
2. `数据构造/数据构造方案.md`
3. 本文件
4. `数据构造/实现审计/controlled_multi_future_runtime_v3_1_implementation_proposal.md/json`
5. `数据构造/实现审计/pilot_attempt_budget_runtime_v3_1_proposal.md/json`
6. `数据构造/实现审计/f1_f4_implementation_registry_v3_1_cpu_current.md/json`
7. `数据构造/实现审计/stage0_readiness_report_runtime_v3_1_current.md/json`
8. `数据构造/实现审计/runtime_v3_1_cpu_static_audit_v3_20260829.json`
9. `数据构造/正式数据构造日志.md` 最新章节
10. `数据构造/实现审计/代码审阅快照/`

## V3 相比 V2 的新增修复

上一版已经完成 target-neutral F1 prefix、raw-derived divergence、family verifier、same-current/anchor职责分层、trace integrity和atomic GPU guard。本版补齐 F3 budget 中此前只有合同、没有完整执行状态机的 conditional correction：

```text
fresh diagnosis scene
→ V→H + return diagnosis
→ only if:
   grasp transform stable
   EEF tracking normal
   classification = pre_release_systematic_offset
→ freeze content-hashed deterministic correction spec
→ one fresh correction scene
→ recheck diagnosis/correction same current + physical anchor
→ at most one correction execution
→ no retry
```

Correction 公式固定为：

```text
T_world_eef_corrected
= T_world_actor_target @ inverse(T_eef_actor_measured_before_release)
```

Correction spec 保存 measured EEF/bottle pose、target bottle pose、original/corrected release、corrected preplace、translation correction、formula、source sample step和 SHA。Verifier thresholds 不可放宽。

以下情况 correction=0：

- grasp slip/contact change；
- EEF tracking failure；
- post-release final dynamics/physics failure；
- diagnosis cleanup uncertainty；
- correction spec hash failure。

以下情况 correction attempt 即使动作成功也不能 accepted：

- diagnosis/correction current hash 不同；
- physical anchor 不等价；
- correction cleanup/planner/verifier failure。

Real F3 CLI 已切换到该 conditional orchestrator；顶层 GPU guard receipt 会汇总 diagnosis+correction cleanup records。

## Current CPU evidence

- Active tests：83/83 passed；
- Vault byte-equal snapshot：83/83 passed；
- 59 Python files compile passed；
- Registry current code hashes：22 项；
- Current root evidence：`数据构造/实现审计/probe_outputs/nonformal_root_pipeline_dry_run_runtime_v3_1_20260829_cpu7/`；
- Root receipt SHA-256：`91396a9b07af1c98d2bc566a56aa8af0a6141278c6d04bca987986cc2d383657`；
- synthetic status=accepted、cleanup=10/10、raw integrity=3/3、prefix hash count=1、first suffix hash count=3、divergence step=2。

## 仍未完成

1. A0 real-SAPIEN smoke 未运行；
2. 所有 concrete adapter/runner仍无真实 GPU evidence；
3. F1 real 3/3、F2 beside、F3 diagnosis/correction、F4 common-X routes均未运行；
4. F3完整三个 programs和F4 A/B/C完整 programs仍 deliberate incomplete/fail-closed；
5. Budget未批准、未冻结；Stage 0禁止。

## 请 GPT 裁决

1. V3 的 F3 conditional correction 是否满足“一次诊断、条件满足时一次确定性修复、其他情况停止”？
2. Diagnosis/correction same-current + anchor recheck 是否充分？
3. V2 的其余 hardening 是否仍有 GPU 前 P0？
4. 是否可以只批准 A0：0 planner、0 action、1 pristine+3 fresh scenes、600秒？
5. 即使批准 A0，也不要自动批准 family actions或Stage 0。

请勿把 CPU/synthetic pass解释成真实 SAPIEN 可行性。
