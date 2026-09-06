# F2 inward planner-only runtime v1

CPU implementation only; actual GPU solver/cache/callback validation is pending.
Entry: `goal_pilot48_v1.f2_inward_runtime_v1.runtime.run(manifest)`.
The caller must validate and hold the new Goal Guard/UUID/lease and frozen source,
asset, input, output and budget bindings. This package never issues authorization.

- One fresh planner-only scene, exactly the fixed C/U_new/D_new IK goals (up to
  three calls if infrastructure stops), fixed 32-seed bank/100 iterations.
- All three endpoints must pass before U_new/D_new/U_new/N, at most four
  trajectory calls. No warmup, old inside gate, hub, yaw, translation or retry loop.
- Zero control execution, collector calls, physical release, raw or accepted root.
- All IK calls have exclusive start/done receipts. Route calls preserve start/done,
  original `_plan_arm` evidence and returned controls. Unknown counts remain unknown.
- New contract preserves the old held-state provenance but binds the new scene;
  this does not establish a physically generated new prefix/current/anchor.

The F2-specific geometric witness identifies only the native tabletop mesh and
verifies the proposed native can footprint/support within the existing 0.1 mm
CPU numerical tolerance. It never uses F3's hold/contact witness. The split
checker preserves robot-versus-full-world checks, while only attached can versus
that one tabletop uses the reduced view. All other table parts remain. Every
nominally valid carry IK solution and every returned carry path is subsequently
screened using native can vertices. All native vertices must stay above and within
the tabletop; D must actually reach the numerical support band. This is a
conservative planner-only geometric gate, not continuous collision freedom,
physical success or proof that a failed task is infeasible.

The released can is frozen at the actual planned D attachment transform rather
than snapped to the nominal target. Full qpos passes explicitly through all four
segments. D->release changes only named gripper qpos to the Robot.set_gripper
open-target formula, rebuilds both single/batch models without attachment and
with the static can, verifies actual locked positions and start-state constraints.
No physical gripper opening is simulated by this diagnostic; successful planning
still requires later physical qualification of the transition.

Tests (CPU):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计:/nfs_share/lijunhui/Robotwin2/project/RoboTwin /nfs_share/lijunhui/Robotwin2/env/bin/python -m unittest goal_pilot48_v1.f2_inward_runtime_v1.test_cpu -v
```

Before running, also pin MPLCONFIGDIR, TMPDIR and XDG_CACHE_HOME inside Robotwin2,
as required by AGENTS. Ten tests passed on CPU on 2026-09-07. No GPU execution
manifest, job, shared log entry or active-source change was made by this subtask.
