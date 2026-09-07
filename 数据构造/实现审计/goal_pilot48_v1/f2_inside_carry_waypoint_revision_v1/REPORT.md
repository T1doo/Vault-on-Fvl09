# F2 inside001 first-target failure and unique carry revision1

The consumed job passed real canonical prefix replay and both full carried
start checks, then its only MotionGen problem failed IK at plan_0. No suffix
motion, descent, release or new box9 contact rule was executed. The actual
side-channel reports IK_FAIL, valid_query=true, internal attempts10 and no
returned endpoint residual; this is one metered solver problem, not ten jobs.

## Evidence and interpretation

The prefix had already raised reported EEF Z to1.0498924255371094m. Reusing the
older controlled-insertion helper added another12cm and requested
Z1.1698924255371095m. The exact original tool/bias/Aloha goal transform agrees
with recorded current-joint URDF FK to1.315micrometres, so the evidence does
not indicate a reported-EEF/solver/world frame mixup. Full single/batch start
states were valid. The high goal failed finite IK; the general URDF chain
triangle bound0.824125m does NOT exclude its0.601415m base distance. We do not
claim mathematical unreachability or a unique self-collision cause without
returned solutions. The concrete implementation problem is that the second
vertical lift was imposed despite an already-cleared prefix state.

The actual held can native lower envelope isZ0.861178402m. Relevant box rim
maxima are aboutZ0.851938m. Thus a fixed-orientation horizontal translation
at the actual prefix height can already cross above the box. The conservative
whole-translation AABB is disjoint from all50 captured world pieces,
including table/box/scale/stand/fixed other arm; its minimum separating-axis
gap is9.240415mm. The saved actually fitted189 can spheres with the unchanged
4mm buffer also have a positive conservative whole-translation bound,
minimum4.256562mm. No mask, radius or buffer was removed for this calculation.

## Only revision1

Preserve actual prefix EEF Z and quaternion; translate EEF XY by the difference
between final inside can XY and actual held can XY. For the saved state this
is EEF[-.3364730636,-.2007584785,1.0498924255], with the same prefix orientation.
It positions the held can above its final inside XY before the unchanged
preinsert orientation/descent. The target's base distance is0.348098m rather
than0.601415m. Smaller distance is a necessary-condition improvement, not a
proof of IK, joint limits, self collision or full robot path success.

The other four target dictionaries, final inside actor goal, actual grasp
transform derivation, layout/current/anchor, approved box9 contact rule and
all numeric physical Gates remain unchanged. There is no alternative height,
pose search, seed search or no-op solver substitution. Total cap remains
5 MotionGen/1fresh/1action/0collection and10 high-level state checks.

The new backend recomputes these native and buffered-sphere bounds from its
fresh actual full-model capture before the first solver call. CuRobo must
still solve the whole robot/full world problem and the actual plan must pass
every existing native sample screen and physical transport/release/final Gate.
The geometric bound proves only the stated straight fixed-orientation can
translation; it does not certify an arbitrary planner trajectory or moving
left-arm geometry. A failed fresh bound stops, without a height adjustment.

Immutable generated CPU evidence: `CPU_REVIEW.json`, receipt
63b37d1619a8f7a166fe353e492ed8eab8787973573a331229d4bd7e298bbe72.
No GPU/scene/IK/trajectory solve or resource reservation was performed by
this CPU audit. New real execution and whole-root qualification remain pending.
