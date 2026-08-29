# GPT review handoff：runtime-v3_3 CPU baseline

当前裁决仍为：

```text
BLOCKED_WITH_REASONS
accepted real roots = 0
Stage 0 = not authorized / 0 trajectories
```

CPU baseline content commit：`be7855e51288d1f977e5eba62660c9056f264242`（已push至`origin/main`）。后续runtime-v3_3 scope request必须绑定该提交或包含本发布回执的后续closeout提交，并同时绑定active source SHA。

GPU前最新加固content commit：`e14b47648043f8145ba989bfa4d8002b446b3abb`；它取代旧source baseline作为后续scope的代码审阅依据。

## 这轮完成了什么

`controlled_multi_future_runtime_v3_3`已把共享prefix从“fresh scene中各自重新规划”改为：

```text
reference scene规划/执行一次
→ seal CanonicalPrefixArtifactV1
→ fresh scene逐step replay同一effective/requested/mask bytes
→ semantic end与settling acceptance分账
→ replay physical Gate
→ suffix从actual replay-end qpos规划
→ seal FrozenSuffixArtifactV1
→ 三个suffix planner全部通过后才在三fresh scenes执行
```

本轮CPU审计还修复了原先会造成错误结论的实现问题：

- actual qpos float64与planner-input float32分别hash；
- v3.3 raw provenance不再误写成v3.1；
- prefix/suffix异常路径保存真实planner query delta；
- F1 green/blue与F4 A/B/C稳定性读取对应actor速度；
- F2 beside release z不再继承prefix的12 cm抬升高度；
- F3 reference和每次replay均硬检shared-first-V、速度、contact和grasp transform；
- F4 completion为连续稳定slot predicate的第一帧，且检查table support、contact continuity、prior slots、non-target与common-X；
- F4 full root前固定执行`A-only→B-only→C-only→A+B noninterference`；
- one-shot authorization绑定parent/request/source/code/budget/family/seed/spec/output/command；root revision使用canonical O_EXCL ledger，revision2必须同slot/seed且source hash不同；
- GPU Guard在source-lock后、消费authorization前再次做fresh-idle UUID snapshot。

## Family CPU状态

| Family | CPU修复 | 下一真实Gate |
|---|---|---|
| F1 | 三色统一4+4 cm lift；terminal qpos/joint margin/waypoint clearance | 3/3 planner→3/3 branch root |
| F2 | official box2；互斥layout；staged inside；release多时点诊断；beside support z | same-can inside/on/beside root |
| F3 | shared grasp/lift/central/first-V artifact与每replay physical Gate | VVHH/VHVH/VHHV root |
| F4 | explicit right cube grasp、no-action IK、A/B/C/AB staged Gate | staged Gate→ABC/ACB/BAC root |

## 验证

```text
official tracked baseline = c3ddfa8b97d5519efa828b075999bd0006778e5e
official tracked worktree = clean
active source tests = 236/236 passed
Vault snapshot tests = 236/236 passed
active/snapshot diff = byte-equal
implementation source SHA-256 = fb51b9d4c2404fcaf130743640e9068019a22ae9a072bdc0d9cf9d1cdc4453ac
budget SHA-256 = 31e9c891bfc49db871f5743debd247ad4d0d6f93a4439e83b2742a99c492e544
```

本CPU baseline没有运行GPU或SAPIEN scene。首次prefix-smoke authorization因GPU0 busy未消费；随后F4 staged failure evidence加固改变source hash，该authorization已明确superseded、不得启动。需要发布v1.1 byte-equal baseline后重新签发fresh namespace，再按顺序运行canonical-prefix smoke、F4 cube IK、F1/F2/F3/F4有限root scopes。

## 建议审阅入口

1. `runtime_v3_3_cpu_static_audit_v1_20260829.json`
2. `f1_f4_implementation_registry_v3_3_cpu_current.md/json`
3. `stage0_readiness_report_runtime_v3_3_cpu_current.md/json`
4. `PRE_STAGE0_RUNTIME_V3_3_SCOPE_BUDGET_V1.md/json`
5. `代码审阅快照/controlled_multi_future/`
6. `代码审阅快照/tests/controlled_multi_future/`

明确边界：没有Stage 0、Stage 1、360条正式数据、训练、H-reveal、compression或π0.5。
