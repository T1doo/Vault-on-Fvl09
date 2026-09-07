# F2-inside native envelope + piecewise floor v1

User-approved design exception only; original verifier files, physical constants,
assets/colliders and historical failures remain unchanged. Approval file hash:
`87fd4deb878eb88f504b2f03330bd5f19b848bc672b03909a3b130a625b37464`.
New verifier ID: `f2_inside_native_envelope_piecewise_floor_v1`.

## Implemented CPU components

- `certificate.py`: exact26-can/15-box ordered native shape registry and scales,
  visible-object coverage by native envelope,7floor/8wall partition, direct-user
  approval/proposal source bindings. Fresh scene certificate construction is
  available and insists on unambiguous single-body shape indexing.
- `geometry_verifier.py`: unchanged exact X/Z side inequalities and Y top
  inequality; real native piecewise floor contact instead of the old Y-bottom
  inset. No raw-grid plane is used as physical floor. All15 box pieces remain
  checked; no collider is removed. Material intersection includes BVH surface
  crossing AND either convex part wholly containing vertices of the other.
- Floor numerical boundary rule: actual intersections must clear when translated
  box-local +Y by the existing F2 native screen's0.1mm numerical band. Persistent
  intersection is rejected. This is a native numerical penetration test, not
  CuRobo sphere padding, a physical-hit threshold change or a continuous proof.
- `contact.py`: actual V8 physical-hit classification unchanged, exact native
  shape index/hash/type/local pose/contact offsets, point/normal availability,
  point-to-material consistency, and actual matching floor contact. Mere pair
  presence or positive separation with no impulse does not count as support.
- `physical_gates.py`: unchanged V10 release/final numerical gates composed with
  the new geometry/floor certificate.50-frame support/release windows,10-frame
  contact confirmation,250-frame settling, velocity/rest/full-open/exclusivity
  checks remain. Native opening geometry is injected into private function
  globals; no original helper is patched. Final containment remains evaluated
  at the final pose, not silently extended to every earlier support frame.

The certificate's shape actor_world_pose/solver_pose fields retain capture
provenance. Evaluation uses the supplied current world actor poses and immutable
body-local geometry; it does not overwrite or mislabel source capture poses.

## CPU verification and limits

15 tests cover the saved native boundary pose, visual coverage, unchanged five
bounds, floating, deep penetration, missing/fake contact, wrong floor/wall shape,
wrong contact-point frame, wrong pose frame/scale/binding, reordered/forged
registry, original release/final speed/rest/window negatives, and original
verifier continuing to fail the historical contact pose.

CPU_AUDIT_V1_1.json supersedes the initial CPU_AUDIT.json for source binding.
Before GPU use an additional negative was added for a can just below the floor
underside with a positive numerical gap: the upward-epsilon material test now
also applies to near-but-not-intersecting pairs. The15th test verifies rejection.
The original CPU audit and unchanged positive geometry/certificate are retained;
no physical job ran between these CPU versions.

Physical-contact positive rows in unit tests are explicitly SYNTHETIC fixtures;
they are not new successful physical trajectories. The saved contact pose is
also only geometric evidence. No real inside support/release success, new raw,
root acceptance, GPU scene or solver call has been produced by this package.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计:/nfs_share/lijunhui/Robotwin2/project/RoboTwin /nfs_share/lijunhui/Robotwin2/env/bin/python -m unittest goal_pilot48_v1.f2_inside_native_floor_v1.test_cpu -v
```

Pin MPLCONFIGDIR/TMPDIR/XDG_CACHE_HOME inside Robotwin2 for native imports.

## Next integration boundary

Use a new supported target derived from the NEW real prefix/grasp transform;
do not retain the suspended mid-cavity target or old gravity-drop executor.
Keep original controlled entry/support→slow release→settle→rest ordering. The
new floor certificate does not itself install a GPU collision waiver: any
planner adapter must keep full robot/world and all sidewall checks, permit only
audited attached-can/floor pairs and screen native planned geometry. Restore
the released-can/open-gripper full-world model before retreat.

Main thread must source-lock this version, integrate actual trace/certificate
provenance, run finite physical qualification and verify three-relation same-
current atomic-root acceptance. No formal360/train/H-reveal/compression/pi0.5
scope is granted by this package or by the narrow geometry exception.
