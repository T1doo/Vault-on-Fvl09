# F2/F3 Post-Gate V2 approved runtime implementation V1

日期：2026-09-04

状态：`IMPLEMENTED_CPU_VALIDATED_NOT_YET_ISSUED`

## F2 revised planner-only Gate

Runtime snapshot: `f2_controlled_insertion_route_gate_run1_runtime_v1/`

- runner SHA-256: `376a782ada5ee95b3e45b09a0af5314516004a4c360f4e9a8e3fb9647f5ace26`
- Guard SHA-256: `bd31e5e1c96190d7b21c27bb775b7346f5127dc7bf0c23e2c4c47edbc50bb1a8`
- sealed prefix-end qpos SHA-256: `8d4cb7b0571c0ba740e0406b32d4041f0dc73f48b0879a4b91567e8445f477b9`
- selected binding SHA-256: `985515944a97b59621067e662b2e33614ebc08c772de74659c01a1c8ae559f0d`
- selected recipe: `f2-final-grasp-v2-r000725`
- inside target hash: `10dd04a9fea671574ddf2cd28209be20938f1df7a3b785c38d7008849539d156`
- beside target hash: `24471cdd00cdc9ef2d983717f68b21141404f66ba6cf337b9f6188d934504817`

The runner verifies five immutable artifacts before use, reconstructs the
sealed actual EEF-to-actor transform, and freezes exactly these ordered
planner targets:

1. `inside_controlled_high_carry`
2. `f2_v2_preinsert_30mm`
3. `f2_v2_controlled_descend_to_support`
4. `f2_v2_retreat_to_preinsert`
5. `f2_v2_neutral`

The separate beside scene freezes layout candidate index 2 at
`[0.08000000000000002, 0.07]m` and retains the existing six-segment route.
The runtime directly restores the sealed 38-D actual prefix-end qpos and can
pose, checks the recomputed EEF pose, target geometry, opening normal and
neutral pose, then calls only the planner. It contains no gripper command,
arm execution, raw writer, video capture, root invocation, or automatic
continuation.

CPU contract validation passed with exact `5 + 6 = 11` target accounting,
`primary_10cm_gravity_drop=false`, and no scene/GPU context.

## F3 zero-scene wiring reissue

Runtime snapshot: `f3_replacement_reissue_run1_runtime_v1/`

- runner SHA-256: `321452f51b99b00543cd144122c2acaf851c226017b582a3c032aece0ef25a78`
- Guard SHA-256: `d79da38bde47f43bc0c2dcd8e6b2628ed2bfe1d6ebd762e3fa933414349914bc`
- approved overlay SHA-256: `586384db1676c3a4ec1cfa78f90f5de624059640da34e2c4707c6681dd9b9347`
- sealed failed runner SHA-256: `36e447e8bc7b9909af4ac88dbf5930c83548d0f6c56db947e6797b7e1c3f4728`
- sealed failed terminal SHA-256: `f9e7d24ae1ad40ce951b359a089cb0ee607ec9302c61db2ed37adae73ed20ef6`

The reissue runner imports only the approved overlay, proves the outer wrapper
still lacks direct `adapter_for`, resolves the five helpers from the inner
sealed base, and dispatches the otherwise unchanged failed runner's
`run_gate`. A CPU contract check resolved retained `f3-final-pose-v3-r0005`
and exactly three replacement candidates without creating a scene or GPU
context.

## Still prohibited

No manifest has yet been issued and no GPU has been used by these runtimes.
F2 physical/root execution, F3 fallback or second reissue, F4 reopening,
Stage 0 rerun, Stage 1, formal 360, training, H-reveal, compression and pi0.5
remain prohibited.
