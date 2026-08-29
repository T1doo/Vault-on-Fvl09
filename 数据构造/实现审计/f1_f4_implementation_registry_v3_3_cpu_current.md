# F1–F4 implementation registry：runtime-v3_3 revision-3 CPU current

```yaml
design_version: controlled_multi_future_f1_f4_v1_2
implementation_version: controlled_multi_future_runtime_v3_3
implementation_revision: runtime_v3_3_revision3_impact_addendum_v1
formal_data: false
stage0_data: false
stage0_authorized: false
accepted_nonformal_roots: 1/4
```

| Family | 固定对象／执行臂 | 最新真实证据 | revision-3 additive repair | Current status |
|---|---|---|---|---|
| F1 | RGB red/green/blue + plasticbox/base3；left | r2 三色 planner15/15、三fresh branches 3/3、root finalizer accepted | 无新物理修复；target-construction callback audit兼容 F1 structured return | `accepted_nonformal_root` |
| F2 | 071_can/base1 + box/base2 + scale/base0 + stand/base3；left | r2 dynamic-settle 3/3与canonical prefix通过；inside在+6cm失败、on 4/4、beside首preplace失败；execution0 | center-aware asset AABB；盒口上方10cm重力落盒；6个固定beside candidates；actual held contact/identity Gate | `revision3_cpu_ready_publication_pending` |
| F3 | 001_bottle/base13 + original pad；left | r2 shared-V EEF negative=39.618mm、grasp drift=52.450mrad失败；reference execution1 | official callback pose唯一绑定cp3/c0；held-envelope clearance raise；same-height 2× carry；pre-V及所有V/H support-contact Gate | `revision3_cpu_ready_publication_pending` |
| F4 | common-X、A/B/C、tray/base0、visible slots；right | r2 common-X 9/9及物理Gate通过；A pregrasp/grasp/lift通过，A_preplace失败；suffix execution0 | A/B/C统一7段block route，插入50% carry midpoint；prior/final slot重查footprint+linear/angular stability+continuous support | `revision3_cpu_ready_publication_pending` |

## 公共实现

- canonical prefix 单次生成、semantic P/settling 分账、exact 26-D bytes/requested/mask replay；
- suffix 从 actual replay-end qpos 链式规划，controls 封存后 fresh execution planner=0；
- current/anchor/fresh scene、3/3 root finalizer、raw 250Hz/N+1、失败/cleanup/orphan receipts；
- official batch-planner API calls与10-pose内部候选分账，callback返回pose可追溯到确切contact/candidate；
- asset `model_data.center × scale` center-aware OBB，用于F2 inside/on/sweep和F3 held envelope；
- physical GPU0–7 any-index fresh-idle policy、per-card lease、per-job cache/HOME/TMP、PID/PGID cleanup、post source-lock/release；
- revision-3仍为single-use、automatic retry=false、recovery=0；旧r1/r2 evidence与ledgers不改写。

## CPU baseline

```text
active tests:   287/287 passed
snapshot tests: 287/287 passed
source/tests diff -qr: zero
implementation_source_sha256:
adc93d707fb2e2fde01b2915f160d769746ea148465f6772b7f4143a02453cb9
budget_receipt_sha256:
7039690e7ceeaf5edbf9c66f853bb116a8757218dd0039795eb8dc12e1f2f8f3
```

Source-bound envelopes：F2=`68 planner / 3 execution`，F3=`96 / 3`（另1次canonical reference execution），F4=`116 / 7`，全部 recovery=0。当前尚未签发或运行revision-3 GPU scope；Stage 0仍为0且未授权。
