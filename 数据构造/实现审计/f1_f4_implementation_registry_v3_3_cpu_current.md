# F1–F4 implementation registry：runtime-v3_3 revision-4 CPU current

```yaml
design_version: controlled_multi_future_f1_f4_v1_2
implementation_version: controlled_multi_future_runtime_v3_3
implementation_revision: runtime_v3_3_revision4_impact_addendum_v1
formal_data: false
stage0_data: false
stage0_authorized: false
accepted_nonformal_roots: 1/4
```

| Family | 固定对象／执行臂 | revision-3真实终止 | revision-4 current implementation | 状态 |
|---|---|---|---|---|
| F1 | RGB red/green/blue + plasticbox/base3；left | r2已accepted，r3未重跑 | 无物理变化；callback audit兼容structured target return | `accepted_nonformal_root` |
| F2 | 071_can/base1 + box/base2 + scale/base0 + stand/base3；left | inside/on planner通过；beside六候选在source/high midpoint失败，execution0 | 不移动stand；历史accepted sector `(-0.15,-0.04)`；support-z≈0.740718；单一6段route与release-boundary table contact Gate | `r4_cpu_ready_publication_pending` |
| F3 | 001_bottle/base13 + original pad；left | clearance carry后pre-V Gate失败，exact predicate因r3证据缺口unresolved | 物理动作完全不变；结构化8-predicate/free-space evidence、partial trace和reference/suffix/branch hashed failure receipts | `r4_evidence_diagnosis_cpu_ready` |
| F4 | common-X、A/B/C、tray/base0、slots；right | common prefix通过；A pregrasp/grasp/lift通过，A_carry_mid失败，execution0 | A/B/C统一60° inward-tilted transform；final actor targets/layout/common/program/verifier不变；MotionGen failure side-channel | `r4_cpu_ready_publication_pending` |

公共链保持 canonical-prefix exact replay、actual-qpos suffix planning/frozen controls、same-current/anchor、250Hz 26-D/N+1 raw、strict family/final-state verifiers、one-shot authorization、GPU0–7 fresh-idle lease/cache/process cleanup。

新增审计完整性：prefix reference/replay Gate异常在scene cleanup前原子保存structured receipt与partial NPZ；failed suffix receipt直接携带planner query table及JSON-safe MotionGen status/error side-channel；F4已完成prior/final full slot state Gate。

```text
active tests: 309/309 passed
snapshot tests: 309/309 passed
source/tests diff -qr: zero
implementation_source_sha256:
3b572172e3a1e5631720ecdc525edbb319d9b980536c2d258be94962e393e416
budget_receipt_sha256:
8d82460bdf943a7a797399ac8c9788c7f30cede522f9c3f65f38cdc2aafc2c4f
```

Source-bound envelopes：F2=`32 planner / 3 execution`，F3=`96 / 3 + 1 canonical reference`，F4=`116 / 7`，全部recovery=0。revision-4 GPU尚未运行；Stage0仍为0且未授权。
