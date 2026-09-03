# F3 reissue V2 budget clarification implementation V1

日期：2026-09-04

状态：`IMPLEMENTED_CPU_VALIDATED_MANIFEST_NOT_YET_ISSUED`

## Lineage

- Source plan SHA-256: `f219a4e57f617b322a9526f939bf9498716f4e428ba220bbd80e64e21e7cfe12`
- Immutable V1 manifest file SHA-256: `efde31a3639df42238bdab354be785c5d6d2975667ee2f4a69dc1d1172197fb2`
- Immutable V1 runner SHA-256: `321452f51b99b00543cd144122c2acaf851c226017b582a3c032aece0ef25a78`
- V1 supersession receipt: `8bca5168b1782f16cabc97163249a24a351d302c825b5c2a55c49d8663bb22b1`
- V1 output, Guard directory and cache/job namespace: all absent
- V1 Guard/scene/planner/physical consumption: all zero

The V1 files remain immutable. The separate receipt marks them
`SUPERSEDED_UNCONSUMED_BY_F3_REISSUE_V2_BUDGET_CLARIFICATION`; V2 keeps the
same reissue ordinal rather than creating a second reissue.

## V2 runtime

Path: `f3_replacement_reissue_run1_runtime_v2/`

- runner SHA-256: `d95d1c71fb3ebdf93d8d4918dad8b5cc2acfc395906be2421952d1aea826136c`
- Guard SHA-256: `57e31200d585120363628fef35401f3f0fc50f6c4ef47bf13d30c8f2b721398d`

The V2 runner hash-binds and calls the immutable V1 execution body, so the
overlay, retained r0005, r1505/r2180/r3677 order, scene binding, physical
Gate, verifier and no-fallback rule are unchanged. It adds an independent
runtime accounting layer:

```text
replacement qualification planner <= 30
each physical candidate planner <= 7
physical candidates <= 4
aggregate planner <= 58
planner scenes <= 6
physical scenes <= 4
aggregate scenes <= 10
no-suffix scenes in this job = 0
reserved next no-suffix scene cap = 3
```

The aggregate value is recomputed from
`replacement_planner_queries + sum(physical_rows[*].physical_planner_queries)`;
it is not copied from the manifest. Planner-scene count is derived from the
three Stage-A rows plus the Stage-B rows actually entered.

## CPU verification

- Both V2 Python files parse successfully.
- Import resolves the immutable V1 runner and approved overlay.
- Synthetic exact worst case `30 + 4*7` reports 58 planner queries and 10
  scenes and passes.
- A synthetic physical count of 8 for one candidate fails both the per-candidate
  and aggregate planner checks.
- No scene, GPU context, output or authorization was created or consumed.

The next safe step is to commit/push this source freeze, then issue a V2
manifest bound to the new HEAD and the immutable supersession receipt, run a
CPU-only Guard preflight, and stop until the ordered F2-first GPU sequence is
available.
