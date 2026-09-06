# F2 fixed-layout U waypoint: endpoint-route revision1

Saved parent: `p48_f2_revision1_001`. D is now fully qualified (four returned
solutions including native support), so this revision does not move the layout
or alter D. C retains eight full-valid solutions.

U80mm can be reached to 2.43 micrometres on a K2-rejected branch. CPU sphere
replay identifies fl_link3/fl_link6 self-overlap about53.3mm, while nearest
world gap remains positive34.4mm. The nearest saved K2+orientation-valid U
state is index15, positional error7.679mm, no self/world overlap. Its residual
points inward/downward, not toward another placement facility.

The single proposal treats that residual direction as a LOCAL estimated
constraint-boundary normal, intersects it by moving U downward only, then
adds one ORIGINAL5mm positional tolerance as a normal-direction margin:

`lower = (norm(error)+0.005)*norm(error)/(-error_z)`.

It produces a32.053084497139554mm lowering and new U-D47.94691550286052mm.
New U z=0.9774614883668223m. No sampled height search or additional solver call
was used. This finite local approximation is NOT a certified boundary, proof
of reachability, or proof that another height cannot work.

`proposal.json` binds all saved IK/capture/world/lineage inputs and CPU sources.
It records11 evenly spaced U→D geometric poses ×1424 native hand/can-world
pairs =15664 pairs, all without forbidden intersection. Native can bottom gap
decreases47.9968→0.04986mm and never penetrates the support beyond the existing
numerical tolerance. The tabletop support exception remains pair-specific;
other obstacles and robot-table checks remain active.

This is hand/can geometry, not a new full-arm IK solution, an actual planned
path, continuous collision checking or physical success. Current D/layout/
orientation/scene seed/physical Gates stay unchanged. A new endpoint-route
spec and fresh C/U/D qualification are required before the conditional route.
