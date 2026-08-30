# F1–F4 implementation registry：runtime-v3_3 revision-5 CPU current

```yaml
design_version: controlled_multi_future_f1_f4_v1_2
implementation_version: controlled_multi_future_runtime_v3_3
implementation_revision: runtime_v3_3_revision5_impact_addendum_v1
formal_data: false
stage0_data: false
stage0_authorized: false
accepted_nonformal_roots: 1/4
```

| Family | 固定对象／执行臂 | 最新真实证据 | revision-5 current implementation | 当前状态 |
|---|---|---|---|---|
| F1 | RGB red/green/blue + plasticbox/base3；left | revision-2 red/green/blue 3/3 accepted | 无变化 | `accepted_nonformal_root` |
| F2 | 071_can/base1 + box/base2 + scale/base0 + stand/base3；left | r4三条suffix planner与execution均启动，全部被合法`fl_link6` palm假阳性Gate截停 | live topology验证palm6，仅作body allowance；finger7/8连续性仍为hard Gate；路线/目标/阈值不变 | `r5_cpu_ready_not_run` |
| F3 | 001_bottle/base13 + original pad；left | r4所有已执行V/H通过；return/release和一次source-integrity mismatch失败 | return controls 2×、target+10mm clearance、assembly contact-free、actual qpos physical release、+250无重接触；V/H不变 | `r5_cpu_ready_not_run` |
| F4 | common-X、A/B/C、tray/base0、slots；right | r4 A planner7/7但cube仅升2.513mm，common-X被推35.4mm | common withdraw+high neutral；actual-open full-window Gate；只做A top-down 20mm micro-lift和common-X/B/C noninterference | `r5_micro_cpu_ready_not_run` |

公共链保持 strict canonical-prefix artifact/replay、fresh scene、same-current/anchor、suffix from actual replay-end qpos、frozen controls、250Hz 26-D/N+1 raw、strict verifier、one-shot GPU Guard 与 ownership-scoped cleanup。

```text
active tests: 339/339 passed
snapshot tests: 339/339 passed
source/tests diff: zero
implementation_source_sha256:
0d19e5d0ace6f3115c686a77485f72b12858023e18dd0cab3fc49f610aa0b33b
budget_receipt_sha256:
ec79e21abc2a2e4c71f47a49df59f6c37c6a8db2bbaf752ac3b28c6af482b535
```

Source-bound envelopes：F2=`32/3/0`，F3=`96/3/0`，F4 micro=`13/1/0`。revision-5 GPU尚未运行；Stage 0仍为0且未授权。
