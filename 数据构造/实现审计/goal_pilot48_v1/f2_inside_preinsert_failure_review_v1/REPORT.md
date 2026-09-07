# Inside carry002: first carry passed, old preinsert endpoint conflicts with hand geometry

## Actual result — not a path/native-screen failure

Plan0 passed, its386 control samples passed the native screen, and the robot
actually executed rows1367–1753. Full held-transport passed; endpoint tracking
error was1.231mm/0.007219rad. The next actual carried refit and both full start
checks passed. Plan1 returned MotionGenStatus.IK_FAIL, valid_query=true,
internal attempts10, no solution/error residual and no control trajectory.
Therefore preinsert/native1/descent/release did not execute. These are two
metered solver problems, not eleven. Main thread owns final Guard/accounting.

Current EEF=[−.3355512,−.1999740,1.0496680]; old preinsert goal=
[−.1497337,−.2003281,.8155320]. This requests +185.8mm X, −234.1mm Z,
and179.79degrees of orientation change. Actual grasp translation drift is
only0.0278mm. Applying the actual post-carry grasp to that goal shifts the
nominal can target by only[−.018,+.004,−.021]mm. Neither loss of grip nor
large grasp-transform drift explains this failure.

## Endpoint necessary conditions

The nominal and actual-grasp-implied can endpoints both pass native world
geometry. The actual189 attached-can spheres, with the original4mm buffer,
have zero negative world pairs. But the target hand/flange is36.4mm below
the box rim. Using actual locked finger qpos and the URDF hand-relative FK,
the configured ten hand spheres have these negative target pairs:

| Link / box piece | Count | Worst gap, original4mm buffer |
| --- | ---: | ---: |
| fl_link6 / box__1 (wall) | 1 | −27.47mm |
| fl_link6 / box__6 (wall) | 1 | −24.18mm |
| fl_link7 / box__4 (floor) | 3 | −8.44mm |
| fl_link7 / box__9 (floor) | 3 | −9.23mm |

Removing the buffer only as a CPU diagnostic still leaves four negative
pairs, including wall overlaps−23.47/−20.18mm. Nothing was actually removed
from the planner. A separate CPU native surface check used the live captured
other-arm link6/7/8 native collision meshes after verifying identical left/
right URDF collision definitions. It also finds palm/box1,4,6,9 and
finger7/box4,9 intersections. This is endpoint geometry evidence, not a GPU
trace of hidden IK candidates. It is substantially stronger than inferring
failure from distance to the shoulder (the target norm is only0.266m).
The approved can–box9 rule does not and must not allow robot/box collisions.

## Where the180degree target came from; semantic boundary

The current factory in f2_controlled_inside_runtime_v2/spec.py maps the
previous saved_contact_geometry.json actor pose into the current box frame,
then derives EEF using the new actual top-down grasp. That old actor pose is
horizontal, quaternion approximately[.7071,0,0,−.7071]. Combining this fixed
old final actor orientation with the new top-down grasp imposes the near180
degree EEF rotation; it is not required by the F2 inside relation itself.

The canonical guide D7.3/D7.7 fixes main object, facility and exclusive inside/
on/beside predicates; it specifies no final object quaternion. The existing
inside verifier likewise checks actual oriented volume, native support,
stability, release and rest, not equality to a prescribed can quaternion.
However changing the final actor orientation is NOT a pure path edit:
it changes the frozen target specification and requires a new declared
target/geometry version and fresh qualification. No old inside target proof,
old failure or accepted root can be silently reinterpreted.

## One fixed preserved-orientation candidate: necessary condition FAIL

Only one alternative orientation has been examined: the actually validated
post-carry can/gripper orientation, without rotation, at the same final XY.
To avoid searching heights, its highest possible actor Z satisfying the
unchanged top boundary was calculated analytically from the native envelope.
That unique top-bound pose has can Z=.750427118 and EEF Z=.938695183;
the native box-Y envelope spans96.618891mm and the top limit is world
Z=.846500019. The original five side/top checks pass at this extremal pose,
but native floor penetration fails on box__5. Thus simply retaining the
upright grasp and removing the180degree rotation is NOT a valid replacement
at this fixed XY: even its highest top-fitting position penetrates the floor.
Lowering it cannot supply a legal top-side supported placement through that
material. No other orientation/height/layout has been sampled.

Status: diagnostic evidence complete; executable pose revision still pending.
Do not issue a known-invalid upright replacement or turn this into another
unchanged planner retry. A next target design must jointly satisfy the
unchanged can volume/floor and the complete hand/world conditions; this report
does not claim to have found such a design or authorize a threshold/mask change.

## Core immutable evidence hashes

- inside_result.json:602c2d31d8dd7702c0ab2206af8b5cd616de0a90a5065eda84ddb61452768441
- qualification_trace.npz:862d48386e6a4ee63c3cb72bb76d7a48bbf2d5959c0d76a9497624cd35cc5559
- model_010_carried_full.json:8e58e0f041d2dafbcc73b23546385e320dc3e3491bb0e805c6f176223c7533de
- old target factory:d61138fbd780d089e8b7f72e93b2126db26f7c09d414032c6d08e6efd9ba2841
- canonical guide:5b24d53718c44fb2a67e79b817c6c4904b82bacf62d4e642ce49470e980b32f9

All calculations were CPU-only, no new IK/planner/scene/action/GPU or budget
write. Existing sources and consumed manifests remain unchanged.
