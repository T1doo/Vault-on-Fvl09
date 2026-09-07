# One analytic axial-roll review: can fits, hand still fails

Source diagnosis is sealed separately as a33dfd377f9f718a38a77ad208a69590f8ddf7af8269fe15e1e1a689fb46ecf0.
This review evaluated exactly one new final orientation, not an angle or
height scan. It changes a final target orientation, not merely a path.

## Derivation and result

Keep the original horizontal can long axis and native-envelope center fixed.
Transform all90 actual native hand vertices into the actual held-can frame.
Under axial roll each vertex's vertical coordinate is a*cos(theta)+b*sin(theta)
plus the fixed center height. The axis origin is inside the convex hull of
these2D coefficients; the unique closest supporting edge gives the exact
roll maximizing the lowest hand vertex. No candidate-angle grid or IK was used.

The resulting roll is−89.870461degrees. Axis/center are unchanged to numerical
precision. Whole-hand lowest height relative to the can axis improves from
−85.955499mm to its mathematical optimum−30.508202mm. The can's actual native
five-boundary/floor checks all pass, including its non-axisymmetric geometry;
axial symmetry was not assumed. The corrected actor pose and actual-grasp EEF
goal are saved in ANALYSIS_001.json, receipt
65cfab9c155077b8b49aa6946a639bdf24310077397461776ca4df077e0d24fa.

However the hand still has native surface intersections with box walls/floor
and the nearby scale. Buffered palm/wall gaps remain approximately−27.45mm
onbox1 and−27.06mm onbox6. Full hand geometry cannot be excused by the approved
can/box9 rule. The actual fitted can spheres additionally overlap floor4/5
as well as9; the existing exception permits only9, not those other pieces.
FLOOR_REVIEW_001.json separately evaluates the approved box9-aware conditions
rather than treating expected can/box9 contact as an automatic rejection.
The candidate still fails for unapproved can pairs and robot/native collisions.

## Floor-height necessity and its limits

The best attainable lowest-hand world Z is.753906454m. The nearest box9 native
support surface point isZ.759257325m: a5.351mm height deficit. The candidate's
can/floor native gap is only8.451micrometres (inside the existing geometry
band), but this is not measured physical support. A helper requiring an
actual surface intersection correctly returned no synthetic contact; the
floor triangle was subsequently located using native nearest-point geometry,
without changing the candidate height.

The supporting facet is slightly sloped, normal[−.024390,.032891,.999161],
not a global constant-Z plane. At the one analytic candidate the minimum
signed hand distances to that actual facet plane are fl6−5.635mm,
fl7−7.787mm and fl8−4.835mm. More directly, native hand/floor4/9 intersections
already exist. Merely moving the walls or the scale while preserving this
floor, target and grasp cannot remove those intersections. A wider box at
the same support height is not thereby a qualified solution; extending the
floor under the low fingers can add contacts rather than remove them.

This does NOT prove that every tilted/translated placement or every larger,
deeper or differently shaped container is impossible. The maximin result is
for the fixed horizontal long axis/center and current closed-grasp transform.
No second roll, different tilt, new center or container was tested.

## Minimal next design impact, not another issuance

Preferred next scope: a new shared-grasp/prefix design whose hand lies above
the supported can at the chosen inside orientation. Before any GPU work,
require one fixed native grasp to pass whole can+hand world geometry at
pregrasp, closed grasp, lifted prefix and supported inside endpoint; test
both all native geometry and configured buffered collision model, not can
containment alone. This addresses the intrinsic current hand–can arrangement
at supported placement. Keep assets/layout and all physical thresholds unless
a separately reviewed design explicitly changes them.

A different option is a genuinely deeper/container design that geometrically
allows upright placement with this top-down grasp. That is not merely
widening the old walls and is not proven by this review. It requires an
audited actual asset/native cavity and new target/support certificates, not
editing the old collision mesh or relaxing its top boundary.

Either a new grasp/prefix or a new layout/container needs a new planned
qualification/current-anchor/prefix lineage and fresh three-relation evidence.
Old on/beside successes remain factual for the old setting, not automatic
qualifications of the new setting. If current bytes happen to remain equal,
retain the same super-root linkage rather than inventing an independent root.
No known-colliding candidate is issued here, and the Goal budget is not reset.
