# One larger same-asset box design — CPU review scope

The old horizontally supported placement and its one optimal axial roll
failed actual hand/floor/wall necessary conditions. This design therefore
uses the already validated upright grasp, but a larger/deeper box so the can
need not be laid horizontally. It is a new container/layout and final-target
design, not a pure planner-path edit or an old failure reinterpretation.

## One deterministic uniform scale, not a scan

Use the same base2 box mesh and a uniform factor, preserving its shape instead
of vertically deforming it. Preserve actual5mm side/top setbacks: scale the
raw cavity geometry first, then subtract/add5mm, not5mm times the scale.

Derive the smallest factor satisfying explicit conservative constraints:
upright native-envelope height plus5mm top allowance must fit above the
highest native floor piece; the complete native hand and configured buffered
hand/can XY envelopes must fit the scaled cavity side bounds. The maximum of
these analytic lower bounds defines the one candidate. This is the minimum
for the stated sufficient envelope conditions, not a claim of globally
minimal physical container size. No list of trial scales or seeds is used.

To avoid creating a scale/box overlap, derive a single compensating box-X
translation that keeps the original rightmost box extent fixed. This is an
explicit layout change. Check its opposite edge against the table and every
other facility; if infeasible, report it rather than trying further scales.

Place the box on the same actual table using its scaled native bottom.
Derive upright can floor-contact height from native triangle geometry at the
fixed scaled cavity center, not by trial heights. Then check native can
containment/nonpenetration, whole closed-hand vertical insertion geometry,
configured model constraints, initial-can separation and table/facility fit.
These are CPU necessary/sufficient geometry checks, not actual physical support,
full-arm IK, a new accepted verifier certificate or new qualification.

## Invariants and required new lineage

Keep F2's three object–facility–relation programs, object asset, execution arm,
physics/physical thresholds,250Hz, geometry5mm boundaries and real native
floor/nonpenetration checks. Do not edit old meshes, contact masks or records.
Uniform asset scale is a new loader parameter, not a hidden modification of
the old captured geometry. New actual native/visual/metadata/shape identity
capture and model binding must later verify the prediction.

The enlarged/moved box changes current RGB/state and layout. Freeze a new
planned current/anchor/candidate/prefix qualification lineage, then revalidate
all three relations in fresh scenes. Old on/beside successes stay historical
successes for the old layout; they cannot be relabeled as new-layout passes.
Old canonical prefix bytes may inform a plan but are not a new successful
prefix or same-current replay certificate. No Stage0 reopening, accepted
root/pilot count, GPU issuance or budget reservation follows from this review.
