# F2 inward 001: saved endpoint diagnosis and one revision

Authoritative CPU analysis: `analysis_v1_1.json`.
Single proposal: `proposal_revision1.json`. No new solver, scene, action or raw.

## What failed

The 96 returned states reproduce the saved GPU FK residuals using independent
URDF FK to within 0.5365 micrometres. C has eight fully valid solutions. U and D
each have eleven states passing the actual recorded K2 checker, but no returned
state reaches the unchanged 5mm position tolerance. This is finite constrained
endpoint failure, not mathematical proof that the task is unreachable.

The absolute closest U/D poses (21.242mm / 13.740mm position residual) are NOT
valid reachable examples: both fail recorded K2. CPU reconstruction of the
locked sphere model finds fl_link3/fl_link6 self-overlap about 53.3/53.4mm; the
closest D additionally overlaps box__8 via fl_link2 by about 6.21mm including
the unchanged world sphere buffer. Do not remove the box or lower collision
checks to force those poses through.

Among existing states passing both K2 and the original orientation metric,
the nearest U is index12 (55.5625mm residual), D index4 (30.1972mm), C index6
(0.000642mm). These are the evidence used for the single revision.

## Unique revision 1

Keep target orientation, height, assets, grasp transform and U-D 80mm unchanged.
Take the saved feasible U pose's XY residual direction after the original goal
coordinate transform, then use the greater projected U/D XY deficit plus ONE
unchanged 5mm position-tolerance margin. This is a deterministic calculation
from saved observations, not a position/seed/orientation sweep.

- Additional XY translation: `[-0.026948511460100494, -0.04959115575834311]` m.
- Magnitude: 56.4403mm.
- Move stand, target and all retained beside candidate coordinates together.
- New active target geometry XY: `[-0.046610392653061564, 0.01219243157674614]` m.
- Distance from U XY to known feasible C region decreases 262.489→236.262mm.
- Native stand/can table support and footprint pass; 1,485 exact moving-stand
  mesh pairs covering facilities, initial/held can and initial/held robot show
  no forbidden intersections. Inside/on disjointness remains true; beside
  radial relation is unchanged by the identical pair translation.

This does NOT establish new IK solvability, a route or physical success.
Issue a new binding/planned slot/current/anchor lineage in a new implementation
version. The next minimum diagnostic remains three fixed K2 endpoints and only
if all pass four carry/release route calls, one scene, zero action/collection.
Do not edit or reissue consumed inward001 artifacts.

## CPU recovery chronology and claim limits

The first CPU sphere diagnostic `analysis.json` applied the world sphere buffer
to self collision too. Its known-valid C exposed this false-positive inference.
Inspection of CuRobo cuda_robot_generator.py:764 confirms it subtracts that
world buffer for self checks. `analysis_v1_1.json` corrects that interpretation:
C now has zero self overlaps, while the selected U/D self overlaps remain large.
The first artifact is retained and superseded for self-collision interpretation.

The first proposal derivation stopped before writing a proposal because it
required 1e-12 agreement between float64 CPU transforms and float32 live SAPIEN
Pose values. Maximum discrepancy was 1.98e-8. The revised diagnostic explicitly
reports this precision gap and checks 1e-7 numeric reconstruction tolerance,
then uses the saved GPU goal itself for residual calculation. No physical,
FK acceptance, IK, contact or family verifier threshold was changed.

Three CPU regression tests pass. Existing model/Guard/meter results remain
primary actual-GPU evidence; the CPU model does not replace those results.
