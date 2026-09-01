# GPT review handoff — next-stage template development V1

## 1. 请先采用的权威总状态

```yaml
protocol: controlled_multi_future_f1_f4_v1_2
implementation_source_sha256: 9873bbe87ed44f7d54003e831ddf9015159036da8078e5cab29ccdc9fcd9fc72

stage0:
  status: STAGE0_COMPLETED_WITH_FAILURE_EVIDENCE
  reopened_or_rerun: false

development_wave:
  status: COMPLETED_WITH_MIXED_TEMPLATE_EVIDENCE
  machine_report: NEXT_STAGE_TEMPLATE_DEVELOPMENT_RESULT_V1.json
  report_sha256: ee374c140c44d4537f95901fcb6a13c0ade018689f939528b1f98bff1af559cf

F1: PASS_5_OF_5_ROOTS_15_OF_15_TRAJECTORIES
F2: FAILED_INFRASTRUCTURE_BEFORE_DEVELOPMENT_EXECUTION
F3: FAILED_PHYSICAL_REAL_PREFIX_EXECUTION
F4: FAILED_PLANNER_A_PREGRASP_IK_NO_FALLBACK

stage1_ready_families: [F1]
stage1_blocked_families: [F2, F3, F4]

canonical_stage1_authorized: false
formal_data_authorized: false
formal_trajectory_increment: 0
training_authorized: false
h_reveal_authorized: false
compression_authorized: false
pi05_authorized: false
```

这里的“F1 ready”只表示F1模板通过了本次development scale pilot；不表示它已经进入formal 360，也不自动授权完整Stage 1。

## 2. 本轮授权范围与明确未授权范围

本轮只授权：

1. F1：5个新独立roots × 3 intents × 1条`r_pc`，目标15条development trajectories；
2. F2：固定官方资产矩阵后的bounded dynamic audit，first-all-Gates后最多1个三分支development root；
3. F3：修正binding后，仅一次3-fresh-scene prefix-only/no-suffix诊断；
4. F4：有限layout search固定选中的c01，仅一次完整planner-only验证；
5. GPU0–7动态fresh-idle、多family跨卡并行；
6. Guard/UUID/lease/source/pre-post/cleanup全部必需。

没有授权：canonical Stage 1、formal 360、模型训练、H-reveal、compression、π0.5或政策训练。

## 3. GPU与审计执行事实

Launch前GPU0–3均为14–15 MiB、0%、P8、无compute process；GPU4–7有外部作业，未使用。最终绑定：

| Family | Physical GPU | Child PID | Guard terminal | Cleanup |
|---|---:|---:|---|---|
| F1 | 0 | 1590995 | `completed` | pass |
| F2 | 1 | 1591173 | `completed_child_failed` | pass |
| F3 | 2 | 1590996 | `completed_child_failed` | pass |
| F4 | 3 | 1591239 | `completed_child_failed` | pass |

四个job均为task-owned cleanup pass、orphan=0、cache cleanup pass、lease release pass、post source-lock pass、GPU回idle baseline。GPU0–3最终为14/14/14/15 MiB、0%、P8、无compute process。没有干预外部GPU4–7进程。

Guard文件SHA：

- F1: `e6771319d744b8e90000a1636a9570a6a8e4659ec89b3aa269100d831f4e7092`
- F2: `ca5ef667e80ea72b201b7bcb44eb856734a670313dda16f8f546d763866b142c`
- F3: `ac35834cff58a2530ec3278d9c83b2973e0ef5b6ab3e71801c4a63be46381796`
- F4: `210e950991e348d0849e024725a5dce3ca4e84e4e9fd9ccf0f1de160178c4c55`

## 4. F1：本轮真正通过了什么

### 4.1 结果

```yaml
accepted_roots: 5/5
accepted_development_trajectories: 15/15
raw_count: 15
mp4_count: 15
root_success_rate: 1.0
planner_queries: 230
execution_attempts: 15
fresh_scenes: 55
recovery_attempts: 0
reserve_activations: 0
formal_increment: 0
```

五个root elapsed：

```text
primary-01: 974.378 s
primary-02: 1046.396 s
primary-03: 868.759 s
primary-04: 875.177 s
primary-05: 870.987 s
mean:       927.140 s
```

每个root严格包含red/green/blue三条真实`r_pc`。五个root具有：

- 5个不同reference-current hash；
- 5种角色—位置轮换；
- 5种candidate display order轮换；
- 每root one canonical prefix artifact；
- 每branch same-current、anchor-equivalence与exact prefix replay；
- 每branch raw、MP4和passing verifier。

逐文件重验结果：15个raw integrity pass、15个MP4 receipt/file hash pass。Raw总计`1,320,648,515` bytes，MP4总计`3,423,408` bytes。

F1 finalizer：

- scope receipt payload: `f72736233275d08265d259b84bb35641598498c31ce66f747be8bf2c394111bd`
- finalizer report: `4049e62baf6c7a5c928c4a8e29f2061fc1f7b079ecd1e286719cab1f8d96ac9b`
- durable report: `F1_BATCH_GENERATION_PILOT_V1_REPORT.json`
- durable report SHA: `dd3d371c54b7abe3b3f54d511a4c848d3262ec67f858e4829456d9a7f92b166c`

### 4.2 能说与不能说

能说：F1当前模板已通过5-root批量生成、自动规划、same-current/shared-prefix、raw/MP4/verifier、位置与候选顺序轮换验证。

不能说：这15条是formal数据；F1已完成R=3；完整Stage 1已ready；F1证据能够替代F2/F3/F4的时间结构证据。

## 5. F2：为什么没有得到新物理结论

### 5.1 运行前设计

F2先完整枚举了：

```text
6 can IDs × 11 box IDs × 5 scale IDs × 5 stand IDs = 1,650 rows
```

CPU full-envelope/layout筛选得到860个static-admissible rows，但动态scope只冻结全局rank 50–61共12个候选，严格按rank顺序，不允许跳过、越界或挑赢家。每候选本应依次做passive-on、layout/mutual-exclusion、same-arm three-chain planner；first-all-Gates后才执行1个inside/on/beside root。

### 5.2 实际失败点

首个候选的场景已经创建，开始生成passive-on audit receipt。但在给receipt计算self-hash时，结构内含NumPy `bool_`，`json.dumps`报错：

```text
TypeError: Object of type bool_ is not JSON serializable
```

结果：

```yaml
status: failed_infrastructure
dynamic_candidate_terminal_receipts: 0
development_execution_count: 0
selected_asset_layout_binding: null
physical_conclusion: null
```

因此不能说rank50物理失败，更不能说12个候选都失败。唯一支持的结论是：F2 dynamic receipt normalization存在实现缺陷。

### 5.3 建议的下一步边界

只修统一JSON normalization，将NumPy scalar递归转换为Python scalar；增加真实receipt hashing regression。旧single-use已消费，必须新implementation/source/namespace。科学候选、rank、布局、planner、release和verifier不得随修复改变。修复后应从rank50重新进入同一个冻结顺序，因为本轮没有形成可验证的terminal candidate receipt。

## 6. F3：现在已经是明确的真实物理失败

旧Closure V1曾因binding接口错误在0 planner/0 execution处失败。本轮V2_1已经修正constructor→reference→fresh replay→receipt→finalizer全链绑定，`close_normalized_target=0.50`真实执行。

本轮计数：

```yaml
planner_queries: 7
prefix_executions: 1
recovery: 0
suffix_planner: 0
suffix_execution: 0
release: 0
```

在第一个reference fresh scene、进入shared-first-V之前，Gate失败：

```text
grasp_translation_stable = false
grasp_orientation_stable = false
selected_gripper_contact_continuous = false
bottle_has_no_pad_or_table_contact = false
```

通俗解释：close=0.50确实执行，但瓶子相对夹爪发生漂移、接触中断，并且没有可靠离开垫子/桌面。因此fail-fast没有运行scene2/3。这次不能再归因于接口。

支持的结论：当前`001_bottle/base13 + 当前grasp pose + close0.50`公共前缀模板不稳定。下一步应进入有限task/asset/grasp redesign impact review，而不是继续微调同一close值或放宽Gate。

## 7. F4：c01在第一预抓取点即被否定

### 7.1 保持不变的内容

common-X、tray、right arm、ABC/ACB/BAC、object-slot mapping、verifier和existing `lower_carry_height` corridor均保持。CPU从6个固定layout candidates中选择c01；没有在线重排。

### 7.2 实际运行

共同prefix reference成功并封存。随后进入ABC fresh scene：

```yaml
canonical_prefix_reference_executions: 1
total_planner_queries: 11
suffix_execution: 0
release_execution: 0
recovery: 0
first_failed_segment: A_pregrasp
planner_status: Fail
motiongen_status: MotionGenStatus.IK_FAIL
```

与Closure V1旧layout“到A_preplace才失败”不同，新c01连A_pregrasp都不可达。本轮还记录到rendered visibility aggregate=false（2个visibility receipts）。按冻结合同立即停止：没有运行ACB/BAC，没有fallback candidate2，没有临时waypoint。

支持的结论：c01不能成为统一F4模板。IK失败与visibility失败应分别处理；不要把调整相机当作解决IK，也不要把调整机械臂目标当作自动解决可见性。

## 8. 当前Stage 1判断

冻结的完整Stage 1需要F1–F4都具备可执行模板。现在只有F1通过，所以：

```yaml
F1_stage1_candidate_ready: true
F2_stage1_candidate_ready: false
F3_stage1_candidate_ready: false
F4_stage1_candidate_ready: false
canonical_stage1_authorized: false
```

F1的15条development trajectories不得混入formal 360，也不能把5 roots当成formal split denominator。若希望单独开展“F1-only Stage 1 subsection”，需要GPT明确裁决这是否应作为一个新的、独立命名的development scope，而不能冒充原canonical Stage 1。

## 9. 希望GPT逐项裁决的问题

请不要只回复“继续修”。请逐项给出：批准／不批准、唯一允许修改项、attempt budget、停止线和需要的输出artifact。

1. **F1**：是否批准一个独立命名的F1-only下一阶段development scope？若批准，Stage-0 root A/B如何完成`r_inv_path/r_inv_motion`，是否仍禁止把本轮15条提升为formal？
2. **F2**：是否批准仅修NumPy scalar JSON normalization后，用相同rank50–61、相同物理语义重新进入dynamic audit？是否必须禁止任何资产/layout/threshold同时变化？
3. **F3**：是否同意正式进入task/asset/grasp redesign？请给有限候选维度，例如bottle model ID、grasp contact point/pose、close target是否固定，并明确最多候选数和first-pass选择规则。
4. **F4**：是否同意放弃c01并进行更高层联合layout+camera review？应先做visibility necessary Gate还是IK Gate？能否在一个bounded candidate-search GPU scope内审计多个候选，但仍只让first full pass进入完整三程序验证？
5. **Stage 1**：完整canonical Stage 1是否继续保持blocked，直到F2/F3/F4各自出现passing template？
6. **Claim boundary**：请确认当前仍只支持F1批量管线可用；尚无F3/F4时间顺序数据、H-reveal、compression或policy-transfer证据。

## 10. 权威文件

- `NEXT_STAGE_TEMPLATE_DEVELOPMENT_RESULT_V1.json` — unified machine result，SHA `ee374c140c44d4537f95901fcb6a13c0ade018689f939528b1f98bff1af559cf`
- `F1_BATCH_GENERATION_PILOT_V1_REPORT.json` — F1 durable audit，SHA `dd3d371c54b7abe3b3f54d511a4c848d3262ec67f858e4829456d9a7f92b166c`
- `stage0_readiness_report_stage0_smoke_v1_2_current.json` — current readiness
- `正式数据构造日志.md` §243–§246 — chronological authorization/GPU/run history

请以machine report与raw/Guard evidence为执行事实；本handoff用于解释和提出下一阶段裁决请求。
