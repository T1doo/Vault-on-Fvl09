# GPT review request after Post-Gate V2 execution V1

日期：2026-09-04
性质：`EXTERNAL_REVIEW_REQUEST_NOT_AUTHORIZATION`

请基于下述终端事实审阅两项精确提案。请不要把本文件视为执行授权，也不要重新开放F4或任何后续阶段。

## 已发生的事实

- F2真实top-contact canonical prefix已通过；三个same-current/anchor/prefix replay均通过；`on` suffix 4/4 planner通过。`inside`与`beside`均在suffix首query报`IK_FAIL`，没有branch/raw/video。
- F3获批replacement job在创建第一个scene前因wrapper helper层级错误终止，实际scene/planner/physical/no-suffix均为0；旧r0005没有重跑，三个新tuple均未开始。
- F4最后一次reopen已经按审阅条件永久封存；本请求不要求第三次reopen。
- Formal accepted仍为`0 roots / 0 trajectories`；Stage 0重跑、Stage 1、formal 360、训练、H-reveal、compression、π0.5仍未授权。

## 决定一：F2 planner-only route Gate

当前sealed prefix-end EEF约为`[-0.280, 0.040, 1.050]m`：

- `inside`首目标约`[-0.149,-0.200,0.906]m`，同时水平转移和下降约144mm，IK失败；提案在它前面新增一个同`xy`、同orientation、`z >= sealed prefix-end z`的高位carry waypoint，后续release/retreat/rest与verifier不变。
- `beside`当前使用冻结layout index 0，即`[0.20,0.12]m`，首个hub IK失败；提案改用同一冻结layout里已存在且仍满足beside互斥关系的index 2，即`[0.08000000000000002,0.07]m`，保留相同六段route、arm、object、stand和verifier。

只申请一次planner-only same-prefix Gate：复用sealed actual prefix-end qpos；inside 4 queries、beside 6 queries，总cap 10；最多2个fresh planner scenes；两条链各执行一次且不fallback。Physical action、branch、raw、video、accepted root、formal全部cap 0。即使两条都pass，也只产生下一次root审阅所需证据，不自动重跑root。

请返回：`KEEP_CLOSED | APPROVE_PLANNER_ONLY_ROUTE_GATE | REVISE`。若`REVISE`，请给出exact targets、caps和stop condition。

## 决定二：F3零scene wiring reissue

精确修复仅把运行时helper引用从outer wrapper改到`outer.base`；不改候选、场景、planner、预算或verifier。CPU preflight已证明outer wrapper确实没有direct `adapter_for`，且inner module的`adapter_for/opened_scene/prepare_f3_scene/record_physical_scene/write_new`五项均callable，candidate/scene/GPU均为0。Overlay SHA=`586384db1676c3a4ec1cfa78f90f5de624059640da34e2c4707c6681dd9b9347`。

若批准，只重发一次原F3 job：

- 保留旧`bottle15/left/lower/contact0/rotation0/r0005`，不重跑qualification；
- 新tuple仍仅为`r1505/r2180/r3677`；
- cap仍为`30 planner queries / 6 planner scenes / 4 physical candidates / conditional 3 fresh no-suffix scenes / 0 formal`；
- 首个implementation/Guard/planner/physical terminal遵循原bounded stop；无fallback tuple、无第二次reissue。

请返回：`KEEP_CLOSED | REISSUE_ZERO_SCENE_WIRING_ONCE | REVISE`。若`REVISE`，请给出exact tuples、caps和stop condition。

## 必须保持的决定

```yaml
f4: CLOSED_NO_REOPEN_REQUESTED
stage0_rerun: false
stage1: false
formal_360: false
training: false
h_reveal: false
compression: false
pi_0_5: false
```

## 建议返回格式

```yaml
f2:
  decision: KEEP_CLOSED | APPROVE_PLANNER_ONLY_ROUTE_GATE | REVISE
  exact_scope_if_revised: null
f3:
  decision: KEEP_CLOSED | REISSUE_ZERO_SCENE_WIRING_ONCE | REVISE
  exact_scope_if_revised: null
f4: CLOSED_NO_REOPEN_REQUESTED
stage0_rerun: false
stage1: false
formal_360: false
training: false
h_reveal: false
compression: false
pi_0_5: false
```
