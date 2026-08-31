# F4 hash infrastructure v13 terminal report

## PASS：基础设施Gate通过，物理corridor全失败

V13完成了exact frozen-neutral binding，并真正调用candidate corridor planner。Infrastructure pass不代表corridor可解；四个预注册候选均返回结构完整的planner failure，因此Stage 0 manifest为F4写入shared preflight blocker，三个F4 attempts将保留失败证据但不伪造trajectory/MP4。

```yaml
implementation: controlled_multi_future_stage0_smoke_v1_1
source: 41a6ede4e2b4dea01e7587ead948358023aeae2972006c31fce076bb96b31063
physical_gpu: 0
total_planner_queries: 32
canonical_prefix_queries: 10
candidate_corridor_queries: 22
execution_attempts: 0
recovery_attempts: 0
hash_infrastructure_pass: true
corridor_selection_pass: false
```

四个candidate均通过：v12 `1e-5m/rad` audit、v13 exact canonical-neutral identity、realized prefix physical equivalence、preplanner contract exact、joint evidence与fresh cleanup。Planner分别使用`6/5/5/6` queries，均无完整可解route；failure=`all_complete_corridors_failed`。

Guard完成、child exit=0、timeout=false、source-lock pass、orphan=0、lease/cache cleanup成功；GPU0回P8/14MiB/0%且无compute。

Evidence namespace tree=`d213da2487c6f36915310d7e65012d0f0bc96f9d1b712532b0caee334db9a2a1`（24 files），Guard tree=`bfe8a0cded41531ffe8c51d949de8b222b5c96e8f7499d08faee0896e6bd5659`。Outer/inner file SHA=`fbf44cc50bff56aa3582a483b5622c2c24426a0758c560a50c1ee0f28c2c905e / 92902766d1eba0b2d89e53faf2210bcf55e7f827b9dcc0c196b413d468092b0a`。

Canonical Stage 0 manifest已生成：`b0e1db84ed883687d4de1caf3426bbef87b297bad3013f31d8ee9f8511eaf69c`，固定12个`r_pc` attempts与每条generated trajectory的MP4合同。Stage 1/formal/training仍禁止。
