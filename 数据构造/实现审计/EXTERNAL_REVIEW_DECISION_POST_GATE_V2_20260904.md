# External review decision after recovery Gates V2

日期：2026-09-04  
来源：`https://chatgpt.com/s/t_6a99999cbbec819181a61f3923f79f6a`  
审阅的 Vault commit：`8e2043bdbf4d4c1ba78bbcf6198f945c3e80027b`

## 决定

### F2

`APPROVE_AS_PROPOSED`

- root invocation cap=1
- planner query cap=75
- fresh-scene cap=8
- robot-action-scene cap=4
- branch cap=3
- development-root cap=1
- formal-trajectory cap=0

使用已冻结并真实通过微门的`can0+box2 / left / contact8 / rotation0`，不再搜索姿态。只运行一个`F2-inside/F2-on/F2-beside` development `r_pc` root，现有suffix、threshold、release-safety和family verifier不变。

### F3

`APPROVE_AS_PROPOSED`

- 保留`bottle15-left-lower/r0005`已有planner survivor，禁止重跑；
- 新tuple精确为：
  - `[bottle5, right, lower_body, contact2, rotation1, r1505]`
  - `[bottle4, left, upper_body, contact0, rotation6, r2180]`
  - `[bottle13, right, upper_body, contact2, rotation5, r3677]`
- planner query cap=30
- planner-scene cap=6
- physical-candidate cap=4
- conditional no-suffix scene cap=3

至少一个新planner survivor后，才可将它与旧survivor进入physical；至少两个physical pass后才触发一次3-scene no-suffix diagnostic。

### F4

`REOPEN_EXACTLY_ONCE_AGAIN`，但只在以下前置条件全部完成后才能签发授权：

1. 本次定性为最后一次Guard-schema repair exception；Run13的root/child/GPU/scene/planner/suffix/branch/raw/video实际消耗全为0。
2. 不得把`PROPOSED_F4_GUARD_COMPLETE_REOPEN2_MANIFEST_V1.json`原地改为approved；必须新建versioned approved manifest。
3. Approved manifest及self-hash必须显式包含`run_id`、`guard_directory`、`cache_directory`和新immutable paths。
4. 可执行Guard源码必须发布到Vault review snapshot并绑定SHA-256。
5. CPU preflight必须调用与可执行Guard相同的manifest/job validation function，禁止再维护独立手写required-field list。
6. 在authorization issuance前，必须对精确approved manifest执行CPU-only production-path subprocess regression，通过manifest load/self-hash/job lookup/source/runner/asset/budget/output checks，并在lease与任何`nvidia-smi`/GPU操作前终止。
7. 同一CPU regression必须调用绑定runner的manifest loading和F4 dispatch selection，证明不会再有pre-child `KeyError`；不得创建scene/output/lease/GPU context或消耗authorization。
8. 保持Run9-qualified candidate/layout/current/anchor/fixed-arm/programs/thresholds/verifiers与上次资源上限不变；禁止candidate search/layout/threshold/program修改、fallback、retry、second root或third reopening。
9. 首个infrastructure/accounting/planner/physical/current/anchor/prefix/verifier/cleanup/orphan failure即终端封存。

F4若完成前置后，上限为`136 planner / 8 fresh scenes / 4 robot-action scenes / 3 branches / 1 development root / 3 development trajectories / 0 formal`。

## 全局边界

`allowed_physical_gpu_indices=[0,1,2,3,4,5,6,7]`。`Stage0_rerun=false`，`Stage1_authorized=false`，`formal360_authorized=false`，`training_authorized=false`，`H_reveal_authorized=false`，`compression_authorized=false`，`pi05_authorized=false`。
