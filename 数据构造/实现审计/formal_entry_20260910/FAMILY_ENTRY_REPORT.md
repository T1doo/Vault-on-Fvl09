# F1 native nine-cell entry: CPU implementation and scope

The executable entry is `family_entry.py --spec SPEC --authorization AUTH --output DIR`.
`--spec SPEC --describe` performs CPU validation and prints the actual call-budget structure without simulator imports. The dispatcher validates the resolved scene/asset hashes and the complete source-file pin before native imports and after execution. GPU execution still requires the separately authorized Guard child; this CPU stage grants no GPU permission.

## Native implementation

- `native_f1.py` subclasses the existing actual F1 adapter/controller. It consumes the passed structured programs rather than rebuilding an old candidate schema. Three real cohorts of three cells produce the nine-cell matrix. Only `r_pc` is the strict shared-prefix cohort; invariance variants are paired with their own program's baseline.
- `native_f1_factory.py` constructs all specified roles, including distractors, from actual pose/size/color/static-state. The source cube remains 44 mm; common box remains model 3. Required cameras are constructed at the specified resolution; head K/extrinsic readback is checked. Installed SAPIEN 3 stubs were checked: fovy is a property, near/far/local-pose methods and remove_camera are available.
- The F1 task geometry gate accepts the complete frozen role set instead of the legacy exact-four-role restriction. It requires the original cube dimensions, larger actual cavity, finite poses, valid subject, and at least 5 mm surface clearance between the three semantic cubes. This replaces the old fixed 80 mm center-spacing implementation restriction. It is only a geometric precondition; native comparative suffix-planner qualification still checks actual grasp/robot feasibility before collection.
- The path variant changes the frozen safe-horizontal waypoint before the real planner/cache stage. Motion variation executes a real bounded post-prefix hold at 250 Hz. No raw noise, retiming of saved data, or relabeling creates variants.
- Every fresh scene's original required RGB, robot state, complete relevant actor/facility anchor, camera config, and capture identity are persisted before action; failed write/readback stops execution. RGB and state are captured without a control step between them.

## Failure and recovery

`native_f1_orchestrator.py` is an isolated copy of the original orchestrator, with two limited changes: first failed branch stops later execution; recovery can reuse verified prior successful cells. Historical source modules are unchanged.

A recovery invocation repeats fresh qualification, actual prefix generation, and suffix preflight. It requires exact regenerated prefix arrays plus root/family/source/current/anchor identity before preserving the old canonical artifact; the new diagnostic generation is retained separately. Each reused branch must pass raw validation and agree in candidate identity and actual frozen suffix controls/targets. Its raw, trace and receipt bytes are copied unchanged with explicit lineage. Only missing cells execute. A maximum of two invocations per cohort is enforced. A checkpoint left RUNNING cannot be retried until the owner reconciles cleanup. A root file lock prevents competing coordinators.

The real production orchestrator fixture regression proves: red succeeds, green fails, blue is not executed; recovery leaves red raw bytes unchanged and executes only green and blue. This is explicitly synthetic control-boundary evidence, not three robot successes.

## Independent disk and model gates

`f1_disk_verifier.py` recomputes subject identity, actual cavity geometry, stable support contact, object/EEF stability, non-task displacement, gripper open state and arm rest from saved arrays and the pre-frozen suffix rest target. It does not consume runner pass. `family_entry.finalize_structure` additionally validates raw contracts, all nine identities, complete current/anchor equality, row0 robot/role alignment, all seven actual prefix fields for `r_pc`, realized path/duration variation, and the real disk-to-input envelope.

`native_raw_contract.py` retains the original numeric/integrity checks but removes its inapplicable historical Stage0-membership predicate. Missing label fields are rejected; old nonformal raw labels are preserved. No label is promoted by this adapter.

A native root may become eligible only if every required gate passes and native physical provenance is present. Synthetic fixtures may pass numeric/semantic checks but retain `native_physical_evidence=false` and `research_eligible=false`. Full Stage1 scientific support remains a separate conclusion.

`f1_portable_export.py` creates an additive, explicitly derived model view with N actual actions, original RGB pixels, and losslessly deduplicated 38+38 robot state. It also copies the complete original native raw/manifest/branch/semantic evidence. No original files change. Source sealing uses a journal, atomic per-file writes, checks existing partial outputs before resuming, and validates every indexed hash on repeated calls. Portable copies use only package-relative model reads.

## Tests and resource bounds

The targeted suite contains 12 CPU cases. It includes native adapter/context construction without scene entry, actual parameter consumption at the simulator construction boundary, failure/recovery through the real copied orchestrator, independent semantic positive/wrong-rest/wrong-relation cases, exact model-source linking, a missing-original-RGB CLI negative case, and a positive complete CLI nine-cell fixture through independent finalization and portable root copy. The copied positive fixture was read with the original source directory disabled. Fixture output remains marked synthetic and formally ineligible.

Per successful full F1 root, the actual call chain has 33 fresh scenes, 21 action scenes, nine collection cells, and a 192 solver-query cap. Each affected-cohort recovery adds `8 + missing_cells` fresh scenes, `4 + missing_cells` action scenes, `missing_cells` collection attempts and at most 64 solver calls. Two invocations per cohort bound a root at 66/42/18/384. Standalone prefix generation and all preflight replay scenes are included. GPU reservation, job timeout, and first-wave dispatch cap must come from the new external contract; none is inferred from old balances or measured CPU time.

No GPU context, physical trajectory, rendering job, training run or formal sample was produced by these tests. Camera rendering, true grasp feasibility in new crowded layouts, actual runtime cost and new-root success rate remain first-wave physical checks.

The first-wave host launcher is described in `FIRST_WAVE_LAUNCHER_REPORT.md`; its CPU tests are additional to the 12 entry tests. F1 renderer allocation is now wrapped by the existing `_PinnedSapienRenderDeviceContextV1`, with binding retained in each original capture receipt.
