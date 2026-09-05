# 我复核后的真实进度

这轮有三项关键进展：

1. **F2 的 inside 路线第一次获得了真实有效的 5/5 planner 正结果。**
2. **F3 已经从“抓不住瓶子”进一步定位成“规划器与真实 SAPIEN 碰撞不一致”，并且逐帧 Gate 已经能提前阻断旧失败。**
3. **F4 Runtime V2.2 已经补完最后一轮权限、持锁和 GPU 冷却问题，现在可以批准一次完整 development root。**

当前仍只有 F1 的 5 个 development roots、15 条 `r_pc` 是验收数据；Stage 1 仍为 `0/48`，formal 仍为 `0/360`。fileciteturn356file0L1-L7

| Family | 当前真实状态 | 下一项 |
|---|---|---|
| F1 | 5 roots / 15 `r_pc` 已验收 | 设计 `r_inv_path`、`r_inv_motion` |
| F2 | inside 5/5；beside 尚未进入 planner | 修正坐标绑定后，只补跑 beside 6 queries |
| F3 | 旧候选 planner 通过、物理 0/4；逐帧 Gate 已实现 | 接入新候选的在线 pre-close executor |
| F4 | 物理模板 3/3；Runtime V2.2 CPU 完成 | **批准一次完整 development root** |

---

# 一、F2：问题已经可以精确定位，不需要再做大范围排查

## 1. Run3 到底成功和失败了什么？

Run3 已确认：

- 短 TMPDIR 修复有效；
- inside 真实执行了 5 次 planner query；
- inside 5/5 全部成功；
- beside planner query 为 0；
- 失败发生在 beside 的目标姿态计算与旧封存姿态进行比较时；
- 没有执行机械臂、没有 raw、没有 root；
- GPU、cache、lease 和进程全部清理干净。fileciteturn357file0L1-L7

因此结论不是：

> beside 路线不可达。

而是：

> beside 路线还没交给 planner，先被一个坐标绑定检查拦住了。

---

## 2. 我从代码中看到的精确根因

当前 sealed contract 对 beside target 的构造方式是：

1. 从一条历史 beside route 中读取 `beside_template_actor_pose`；
2. 历史 route 原本对应的是旧 candidate；
3. 构造 candidate 2 时，代码直接执行：

```python
expected = beside_template_actor_pose.copy()
expected[:2] = candidate_xy
```

也就是简单把历史 actor pose 的 XY 改成：

```text
[0.08000000000000002, 0.07]
```

但 live 目标不是这么算的。Live 代码调用：

```python
_actor_pose_centered_on_support(...)
```

它会根据：

- 罐子的碰撞几何中心；
- 罐子姿态；
- 碰撞几何 half extents；
- 桌面高度；

重新计算**actor origin**，确保“罐子的几何中心”而不是“actor 原点”落在 candidate XY。fileciteturn359file0L1-L7 fileciteturn381file0L1-L7

罐子 base0 的局部几何中心并不严格为零：

```text
[-0.0000029668, 0.0477637092, -0.0000036195] m
```

姿态又是：

```text
[0.5, 0.5, 0.5, 0.5]
```

因此 actor origin 的 XY 必须带一个约几微米的补偿，不能直接等于 candidate XY。fileciteturn401file0L1-L7

按冻结几何计算，这个补偿大约为：

```text
Δx ≈ +0.000003619492 m
Δy ≈ +0.000002966821 m
```

所以正确 actor origin 大约是：

```text
x ≈ 0.080003619492
y ≈ 0.070002966821
```

而旧 `expected[:2] = candidate_xy` 把这个补偿抹掉了。两者位置差约：

```text
4.68 × 10⁻⁶ m
```

当前代码容差却只有：

```text
1 × 10⁻⁶ m
```

于是它必然触发：

```text
F2 live beside index-2 target differs from sealed layout
```

这里不是建议放宽容差，而是要**修正坐标语义**。

---

## 3. F2 正确修法

不要再把一个历史 actor pose 当成模板，然后只覆盖 XY。

应当从以下冻结语义重新生成 candidate 2 的 pose：

```text
candidate_xy
+ table plane
+ frozen object orientation
+ frozen local geometry center
+ frozen half extents
```

更稳妥的独立校验方式是：

```python
world_center_offset = R(object_orientation) @ local_geometry_center

actor_origin_xy = candidate_xy - world_center_offset[:2]
```

然后检查：

```text
compose_pose(corrected_actor_pose, local_geometry_center).xy
== candidate_xy
```

而不是检查：

```text
corrected_actor_pose.xy == candidate_xy
```

### 必须增加的 CPU 回归

```text
1. old_xy_overwrite_rejected
2. geometry_center_lands_on_candidate2_xy
3. actor_origin_contains_rotated_local_center_compensation
4. candidate0_template_translated_to_candidate2_matches_canonical_recompute
5. orientation unchanged
6. support plane unchanged
7. beside six segment order unchanged
8. inside Run3 receipt not consumed or rerun
9. target derivation failure still writes scene cleanup receipt
```

第 9 点也要修。当前 `run_gate()` 是在 `with opened_scene(...)` 完成后才把：

```python
cleanup = context.cleanup_receipt
```

写进结果；如果 `_derive_live_targets()` 中途抛异常，就没有 beside 专属 cleanup receipt。Run3 正好暴露了这一点。以后应在 `finally` 中始终封存：

- scene instance；
- planner before/after；
- target derivation；
- cleanup；
- error。

---

## 4. F2 下一次不要再跑完整 11-query Gate

Inside 已经真实通过，不能为了 beside 再浪费一次 inside。

我批准的下一范围是：

```yaml
f2:
  decision: APPROVE_ONE_F2_BESIDE_ONLY_ROUTE_COMPLETION_AFTER_CPU_FIX_V1

  supersedes_no_fourth_full_dispatch: true
  full_11_query_rerun_authorized: false

  preserved_evidence:
    inside_source: F2_RUN3
    inside_planner_queries: 5
    inside_planner_pass: true

  new_execution:
    relation: beside
    candidate_index: 2
    planner_queries: 6
    fresh_scenes: 1
    physical_executions: 0
    branch_executions: 0
    raw_trajectories: 0
    videos: 0
    accepted_roots: 0
    formal_trajectories: 0

  unchanged:
    - candidate XY
    - selected can and box
    - selected arm
    - planner seed
    - six-segment route
    - beside annulus
    - neutral target
    - no gravity drop
    - no target search
    - no fallback

  required_before_execution:
    - publish a canonical semantic-target derivation artifact
    - pass the nine CPU regressions above
    - issue a new beside-only manifest
    - bind the Run3 inside receipt and corrected beside target hash
    - use a new output/Guard/cache namespace
    - complete CPU Guard and runner-entry preflight
```

如果 beside 6/6 通过，再生成一份组合资格 receipt：

```text
Run3 inside 5/5
+
beside completion 6/6
=
F2 route qualification 11/11
```

这个组合 receipt 通过后，才进入 `F2TopContactControlledInsertionRootV2`。不要再回到旧 gravity-drop root。

---

# 二、F3：逐帧 Gate 已经做对，当前主要缺“在线执行接线”

## 1. 当前根因已经比较可靠

旧四个候选不是 planner 不可解，而是 planner 通过后，机械臂在真实 SAPIEN 执行中发生：

- 执行臂自碰；
- 执行臂撞桌面或垫子；
- EEF 和关节跟踪误差过大；
- 部分候选在闭爪前就推动了瓶子。

所以最后出现的“lift 后接触率 0、瓶子没离桌”只是这些更早错误的后果。fileciteturn320file0L1-L7

---

## 2. Full-window Gate V1.1 是有效修复

新版不再只看 pregrasp 和 grasp 的结束点，而是检查整个 segment：

```text
start + 1 ... end
```

并且会记录：

- 第一帧失败位置；
- 第一对失败 contact pair；
- 最大瓶子位移；
- 最大碰撞冲量；
- 最小 signed separation；
- endpoint 的 qpos/EEF tracking。

任何一帧发生真实自碰、撞桌、撞垫、提前碰瓶子或信号缺失，都会在 close 前阻断。fileciteturn384file0L1-L7

8 个测试已覆盖：

- 运动中瞬时自碰；
- 瞬时支撑面碰撞；
- 瓶子被撞开后又返回；
- 中间帧 contact signal 缺失；
- 缺帧；
- 正间距假接触；
- 不完整碰撞 pair。fileciteturn386file0L1-L7

对旧四条 trace 的完整窗口重放也全部在 close 前拒绝；例如 r0005 的 pregrasp 窗口检查了 629 行，第一处失败出现在 row 388，而不是等到 lift 后才发现。fileciteturn360file0L1-L2

因此 **Gate 本身可以保留，不需要再设计 V1.2。**

---

## 3. 四个新候选已经固定，但 rule hash 还不能作为执行依据

当前冻结文件里的四个候选 ID 和 recipe SHA 都正确：

1. `r3063`
2. `r0861`
3. `r1401`
4. `r2526`

但同一文件也诚实地写着：

```yaml
external_rule_hash_recomputed: false
external_rule_payload_available: false
```

所以旧的：

```text
e2d795...
```

不能继续被当作机器可复核的 rule authority。fileciteturn361file0L1-L7

最简单的解决办法不是再猜旧 hash，而是：

> **直接把四条 exact recipe 及其 SHA 作为冻结事实源。**

新增：

```text
F3_DETERMINISTIC_CANDIDATE_FREEZE_RESOLVED_V1.json
```

内容必须明确：

```yaml
universe_sha256: 4bc99d0957dcd2dd955e6060cbe2a077cec1a2cd71ef7eecf1eca9375b16de46

excluded:
  - r0005
  - r1505
  - r2180
  - r3677

ordered_candidates:
  - id: r3063
    sha256: e612c0a829559966bae718bd3a995fe4d87b731de2680c38a56f325cedf2fb79
  - id: r0861
    sha256: 546859c30a0d068f1ca8103e5def09a450a84016980d766d479949d908ceadbd
  - id: r1401
    sha256: 599934ea0592589f4daa7b9daffc72c42a5a527ce2bd50911fd3b85a80ee883d
  - id: r2526
    sha256: 2b9c30ea466d6350b04add4102eda9aa004f22f9589224284ed5851dd681b5ae

online_search: false
fallback: false
seed_retry: false
success_conditioned_substitution: false
```

这四条 recipe 与 3840 条 universe 的确定性枚举顺序一致。fileciteturn337file0L1-L7

---

## 4. F3 executor 应怎样接

不能再调用旧的：

```python
execute_f3_level2_physical_v1(...)
```

因为旧函数的顺序是：

```text
execute pregrasp
execute grasp
立即 close
```

中间没有接 full-window Gate。fileciteturn346file0L1-L7

应新建：

```text
f3_preclose_candidate_micro_runtime_v1/
  manifest_contract.py
  guarded_launcher.py
  job_runner.py
  candidate_executor.py
```

每个候选按下面顺序执行：

```text
Stage A planner：pregrasp / grasp / lift
Stage B planner：保持现有 7-query qualification
        ↓
新 fresh physical scene
        ↓
只规划 pregrasp / grasp / 25mm micro-lift
        ↓
执行 pregrasp
        ↓
立刻对完整 pregrasp segment 执行 V1.1 Gate
        ↓
失败：停止，绝不 close
通过：执行 grasp
        ↓
立刻对完整 grasp segment 执行 V1.1 Gate
        ↓
失败：停止，绝不 close
通过：close 0.50
        ↓
hold 250
        ↓
执行 frozen 25mm micro-lift
        ↓
contact continuity / off-support / transform Gate
        ↓
停止，不执行 shared-V
```

### 精确预算仍保持

```yaml
candidate_cap: 4

qualification:
  10_queries_per_candidate: 40
  scenes: 8

physical_micro:
  3_queries_per_candidate: 12
  scenes: 4

aggregate:
  planner_queries: 52
  scenes: 12

shared_v: 0
no_suffix: 0
root: 0
raw: 0
formal: 0
```

达到两个 physical pass 后立即停止。

目前 F3 仍然需要一次窄范围复审，因为 candidate-bound executor 和 Guard 尚未完成；latest checkpoint 也明确记录 `runtime_integration_complete=false`。fileciteturn388file0L1-L7

---

# 三、F4：V2.2 已满足要求，正式批准一次 root

## 1. V2.2 已完成哪些关键修复？

现在已经具备：

- `approved / GPU / planner / scene / physical / root` 六层权限显式一致；
- proposal 与 approved 状态分离；
- 不再用 Markdown 字符串包含判断授权；
- 使用结构化 exact decision；
- runner entry 验证 Guard 正持有 exclusive flock；
- cache、UUID、GPU index、lease、环境变量全部绑定；
- child 结束后最多 13 次、每次间隔 5 秒轮询 GPU baseline；
- 轮询期间 lease 始终保持；
- transient P0/高利用率能够等待到 P8/0%；
- UUID 变化、永远 busy、snapshot error 均 fail closed；
- V2.1 finalizer 原样保留。fileciteturn373file0L1-L7 fileciteturn375file0L1-L7

CPU 生命周期测试还证明 parent 的真实 exclusive flock 已持有，runner entry 能正确验证，同时没有调用 GPU、planner、scene 或 production output。fileciteturn363file0L1-L2

Proposal 继续冻结：

- r01；
- `ABC / ACB / BAC`；
- right prefix / left suffix；
- 136 queries；
- 11 scenes；
- 7 action scenes；
- 3 raw；
- 3 MP4；
- 最多 1 root、3 trajectories；
- formal 0。fileciteturn365file0L1-L2

## 2. F4 正式决定

```text
F4_ONE_ROOT_AUTHORIZED_RUNTIME_V2_2
```

兼容当前 `exact_root_decision()` 的结构化决定主体如下：

```json
{
  "schema_version": "cmf_external_execution_decision_v1",
  "decision": "F4_ONE_ROOT_AUTHORIZED_RUNTIME_V2_2",
  "authorized": true,
  "candidate": "f4-slot-corridor-hv2-r01",
  "programs": [
    "F4-ABC",
    "F4-ACB",
    "F4-BAC"
  ],
  "maximum_root_invocations": 1,
  "maximum_accepted_development_roots": 1,
  "maximum_accepted_development_trajectories": 3,
  "maximum_formal_trajectories": 0,
  "review_base_vault_head": "fefb7c2adbd374ea29e9a3f33461f5e2dfb43a93",
  "proposal_manifest_sha256": "53261fe88f3ef31e41e8f2c1f685d2b21cf1ec9f8ef8aa6430270ec46420d385",
  "runtime_sha256": {
    "manifest_contract.py": "10716c654fadf26bf0dd690e24582830c2ab1c03afa37d42c86c29b6c0dbcf71",
    "guarded_launcher.py": "23c234b4188339986d06d5b0b9defae5e5cb8da48283f5033692d037d2db12d2",
    "job_runner.py": "7b47e1a7e3ad9fd0db528e23ee9d870029d527c5b2f47a3550fc545d3a257463",
    "lifecycle_preflight.py": "980d7b7c58e313ace42d6b057e607f562bf48b0cca0b24e73b24a5806bf63907"
  },
  "hardening_receipt_sha256": "0ed086424ad68309a8584e8c4862b26843912d9ad7e025589a92507583a3f88e",
  "stage1_authorized": false,
  "formal_360_authorized": false,
  "training_authorized": false,
  "h_reveal_authorized": false,
  "compression_authorized": false,
  "pi05_authorized": false
}
```

Codex 应：

1. 把本条回复保存为版本化 Markdown decision 文件；
2. 计算该 Markdown 的 file SHA；
3. 在上面 JSON 中增加：

```json
"authoritative_message": {
  "path": "<保存后的 decision Markdown 路径>",
  "file_sha256": "<该 Markdown 的真实 SHA-256>"
}
```

4. 再计算整个 JSON 的 `receipt_sha256`；
5. 生成新的 approved manifest：
   - 六层 execution authority 全部 `true`；
   - `root_status=ONE_DEVELOPMENT_ROOT_AUTHORIZED`；
   - 绑定 decision Markdown 和 JSON receipt；
   - 使用新 run ID、output、Guard 和 cache 路径；
6. 运行一次 `require_execution_authorized=true` 的 CPU preflight；
7. 连续两轮 fresh-idle 后，执行唯一一次 F4 root。

不得为了版本名称整洁去修改这些冻结字符串：

```text
ONE_F4_DEVELOPMENT_R_PC_ROOT_V2_1
cmf_f4_development_root_v2_1_...
```

它们虽然名字仍带 V2.1，但当前 V2.2 contract 有意复用，改名只会造成无意义的 hash churn。

---

# 四、接下来最高效的顺序

## 现在立即并行做 CPU 工作

### 轨道 A：F4 发布执行包

```text
保存本次外审
→ 生成结构化 approval receipt
→ 生成 approved manifest
→ execution-authorized CPU preflight
→ push
```

### 轨道 B：F2 beside 修复

```text
证明约 4.68 μm actor-origin 补偿
→ 修正 semantic target freeze
→ 9 个 CPU 回归
→ beside-only 6-query manifest
→ CPU preflight
```

### 轨道 C：F3 接线

```text
固化 exact candidate list
→ online full-window Gate
→ candidate-bound executor
→ Guard/runner
→ 52-query/12-scene accounting tests
→ 新窄审阅包
```

### 轨道 D：F1

纯 CPU 设计：

```text
r_inv_path
r_inv_motion
same-intent/different-realization verifier
root-atomic 9/9 finalizer
```

---

## GPU 调度顺序应改为

现在 **F4 已经是最成熟的一族**，不应继续等 F2/F3。

```text
F4 approved manifest + preflight
        ↓
F4 唯一一次 development root
        ↓
clean postcheck
        ↓
F2 beside-only 6-query completion
        ↓
clean postcheck
        ↓
F3 candidate micro-Gate 获批后运行
```

三族仍不能并行使用 GPU。

单个 family 的科学失败不阻塞其他 family；只有以下情况阻塞总队列：

- cleanup 失败；
- orphan process；
- GPU baseline 未恢复；
- UUID/index 改变；
- terminal 或 artifact 无法完整封存。

---

# 五、可直接交给 Codex 的总指令

```yaml
review_base:
  vault_head: fefb7c2adbd374ea29e9a3f33461f5e2dfb43a93
  stage0_rerun: false
  stage1: false
  formal360: false
  training: false
  h_reveal: false
  compression: false
  pi05: false

F1:
  status: 5_DEVELOPMENT_ROOTS_15_RPC_ACCEPTED
  next:
    - design_r_inv_path_cpu_only
    - design_r_inv_motion_cpu_only
    - design_root_atomic_9_of_9_finalizer
  gpu_authorized: false

F2:
  status: INSIDE_5_OF_5_PASS_BESIDE_NOT_PLANNED

  root_cause:
    classification: ACTOR_ORIGIN_VS_GEOMETRY_CENTER_BINDING_ERROR
    explanation: >-
      The frozen expected beside pose overwrites actor-origin XY with
      candidate XY, while the live pose compensates for the rotated
      nonzero local collision-geometry center. Do not relax tolerance.

  required_cpu_fix:
    - derive candidate2 actor origin from frozen geometry-center semantics
    - verify composed geometry-center XY equals [0.08000000000000002, 0.07]
    - preserve approximately 3.619492e-6 / 2.966821e-6 actor-origin correction
    - preserve orientation, support plane, candidate index and six targets
    - write scene cleanup and target-difference receipt on every exception path

  conditional_execution_decision:
    decision: APPROVE_ONE_F2_BESIDE_ONLY_ROUTE_COMPLETION_AFTER_CPU_FIX_V1
    inside_rerun: false
    beside_queries: 6
    fresh_scenes: 1
    physical: 0
    branch: 0
    raw: 0
    root: 0
    formal: 0
    fallback: false
    search: false
    retry: false

  after_pass:
    - combine Run3 inside receipt and beside-only receipt
    - require exact 5+6=11 composite qualification
    - then prepare F2TopContactControlledInsertionRootV2 proposal
    - never reuse gravity-drop root

F3:
  status: FULL_WINDOW_GATE_READY_RUNTIME_NOT_INTEGRATED
  gpu_authorized: false

  candidate_authority:
    do_not_bind_unavailable_external_rule_hash: true
    bind_exact_candidate_ids_and_recipe_sha256s: true
    candidates:
      - [r3063, e612c0a829559966bae718bd3a995fe4d87b731de2680c38a56f325cedf2fb79]
      - [r0861, 546859c30a0d068f1ca8103e5def09a450a84016980d766d479949d908ceadbd]
      - [r1401, 599934ea0592589f4daa7b9daffc72c42a5a527ce2bd50911fd3b85a80ee883d]
      - [r2526, 2b9c30ea466d6350b04add4102eda9aa004f22f9589224284ed5851dd681b5ae]

  runtime:
    - do_not_call_execute_f3_level2_physical_v1
    - plan_pregrasp_grasp_25mm_lift_for_physical_micro
    - execute_pregrasp_then_full_window_gate
    - execute_grasp_then_full_window_gate
    - close_only_if_both_windows_pass
    - hold_250_then_25mm_micro_lift
    - stop_after_contact_off_support_transform_gate
    - no_shared_v
    - no_suffix
    - no_root
    - no_raw

  exact_caps:
    planner_queries: 52
    scenes: 12
    physical_attempts: 4
    stop_after_physical_passes: 2

  second_review_before_gpu: true

F4:
  decision: F4_ONE_ROOT_AUTHORIZED_RUNTIME_V2_2
  authorized: true

  candidate: f4-slot-corridor-hv2-r01
  programs: [F4-ABC, F4-ACB, F4-BAC]
  canonical_prefix_arm: right
  suffix_arm: left

  caps:
    root_invocations: 1
    planner_queries: 136
    fresh_scenes: 11
    robot_action_scenes: 7
    branch_executions: 3
    raw: 3
    videos: 3
    accepted_development_roots: 1
    accepted_development_trajectories: 3
    formal: 0

  required_before_gpu:
    - save this external decision as Markdown
    - generate exact self-hashed JSON approval receipt
    - issue a new approved manifest bound to the receipt
    - all six execution authority fields true
    - root_status ONE_DEVELOPMENT_ROOT_AUTHORIZED
    - execution-authorized CPU preflight
    - all output, Guard and cache paths absent
    - commit and push
    - two stable fresh-idle GPU snapshots

  retry: false
  fallback: false
  seed_retry: false
  candidate_search: false
  second_root: false
  automatic_stage1: false

execution_order:
  - F4_one_root
  - clean_GPU_postcheck
  - F2_beside_only_completion
  - clean_GPU_postcheck
  - F3_candidate_micro_after_second_review
```

**当前最重要的变化是：F4 已经可以进入一次真实 root；F2 不需要重跑 inside，只需修正几微米级的坐标口径后补 beside；F3 的 Gate 已经可靠，剩下的是把它真正接到闭爪之前。**

---

If you want, I can:

- 生成F2修正语义的详细技术步骤
- 设计F3执行器的具体接线实现方案
- 制定F4完整root批准与执行的自动化流程
