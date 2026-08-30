# 给GPT的审阅交接：Stage 0 smoke v1 F4 infrastructure终端结果

请以Vault当前最新commit为准审阅，不要把CPU pass或canonical-prefix planner query误当作F4 corridor Gate通过。

## 当前裁决

```text
BLOCKED_WITH_REASONS
Stage 0 = 0/12
Stage 0 manifest = not created
Stage 1/formal/training = unauthorized and not run
```

## 本轮做了什么

1. 发布`controlled_multi_future_stage0_smoke_v1`的CPU/审计基线，active/snapshot `481/481` tests通过，source=`b312fca095687beb4c113cc59761692bef5667230ea9eb462b673b9dbcbf0d05`。
2. 在用户明确批准后签发并消费唯一single-use F4 hash-infrastructure authorization。
3. 在physical GPU0运行planner-only Gate：最大48 planner、0 execution、0 recovery、7200秒，无自动retry。
4. 完整保留成功与失败证据，并确认所有scene、GPU lease、cache和task-owned process安全释放。

## 真实结果

Pristine current/anchor、canonical prefix和exact corridor contract均成功。总planner query=`10`，但全是canonical prefix query；candidate corridor query=`0`。

第一个candidate `r4_successful_carry_orientation_and_corridor`：

- candidate design payload exact：pass
- ordered segment IDs exact：pass
- layout/right arm/release semantics unchanged：pass
- frozen/reconstructed candidate各自self-consistent：pass
- `A_pregrasp`至`A_release`七段pose error：全部0
- `A_neutral` position error：`0.11746700969074096 m`
- `A_neutral` orientation error：`0.007997776852024735 rad`
- preregistered tolerance：`1e-5 m / 1e-5 rad`

因此v12正确fail closed；不能用更宽容差把它解释成raw-float噪声。

## 当前根因判断

`_top_down_full_targets_v8()`把suffix neutral取自`repaired_common[-1]`；该值又来自common route的`common_center_high`。冻结contract在pristine scene生成，但fresh candidate是在canonical prefix replay之后重建，此时`common_x`已从source移动到tray。Legacy common target builder会根据当前`common_x`重算common lift/preplace/center-high，因此terminal `A_neutral`变化；A与slot未移动，所以其他七段保持精确一致。

Trace进一步确认A/slot_A不动，而common_x移动`0.228714m`、旋转`0.007997776852rad`；neutral的orientation error与该旋转完全相同。冻结A_neutral等于canonical prefix `target_neutral_pose`，不是layout中已被prefix repair supersede的旧branch-neutral，因此不要把“切回layout neutral”当成修复。

建议重点审阅：

1. 上述因果定位是否充分；
2. 最小collector修复是否应仅在v12 fresh reconstruction中将terminal neutral override为frozen candidate/canonical replay target、验证二者一致并重算hash，而不是post-prefix `common_x`或旧layout neutral；
3. 该修复是否保持layout、right arm、program、release target、verifier和科学设计不变；
4. 新版本是否只需CPU/static审计和一个新的single-use F4 infrastructure probe；
5. 在新Gate真正产生至少一个candidate corridor planner query以前，继续禁止Stage 0是否正确。

## 主要审阅入口

- `数据构造/实现审计/F4_HASH_INFRASTRUCTURE_V12_TERMINAL_REPORT_20260830.md`
- `数据构造/实现审计/F4_HASH_INFRASTRUCTURE_V12_TERMINAL_REPORT_20260830.json`
- `数据构造/实现审计/F4_HASH_INFRASTRUCTURE_V12_STAGE0_SMOKE_V1_FAILURE_EVIDENCE_MANIFEST_20260830.json`
- `数据构造/实现审计/F4_HASH_INFRASTRUCTURE_V12_STAGE0_SMOKE_V1_GUARD_EVIDENCE_MANIFEST_20260830.json`
- `数据构造/实现审计/stage0_readiness_report_stage0_smoke_v1_current.md`
- `数据构造/实现审计/probe_outputs/prestage0_f4_candidate_hash_infra_v12_seed20260829_run1/receipt.json`
- `数据构造/实现审计/probe_outputs/prestage0_f4_candidate_hash_infra_v12_seed20260829_run1/F4_hash_infrastructure_v12/receipt.json`
- `数据构造/实现审计/probe_outputs/prestage0_f4_candidate_hash_infra_v12_seed20260829_run1/F4_hash_infrastructure_v12/candidate_1/equivalence_receipt.json`
- `数据构造/实现审计/gpu_guards/controlled_multi_future_stage0_smoke_v1/prestage0_f4_candidate_hash_infra_v12_seed20260829_run1.guard.json`
- `数据构造/实现审计/代码审阅快照/controlled_multi_future/f4_corridor_selection_gate_v12.py`
- `数据构造/实现审计/代码审阅快照/controlled_multi_future/family_runners_v3_3.py`

## Claim boundary

当前只能说：canonical F4 prefix在该scene可执行，v12找到了一个新的、可归因的branch-neutral provenance软件问题，且安全/失败留存机制正常工作。

不能说：F4 corridor通过、F4 Stage 0可行、Stage 0已开始、已产生12条数据、正式数据已生成，或训练/Temporal/H-reveal/compression/π0.5已开始。
