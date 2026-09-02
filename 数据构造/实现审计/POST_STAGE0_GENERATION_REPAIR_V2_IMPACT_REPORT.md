# Post-Stage-0 F2/F3/F4 Generation Repair V2

Status: `CPU_CODE_GENERATION_REPAIR_IMPLEMENTED_AND_VERIFIED_NO_EXECUTION_AUTHORIZED`

## Corrected earliest failures

- F4 legacy `f4-slot-corridor-hv1-r01` is `INVALID_BY_CONSTRUCTION_TARGET_OVERLAPS_UNMOVED_OBJECT`. ABC/ACB place A into B; BAC places B into A. It must not be rerun.
- F3 V2 is `TARGET_MUTATED_AFTER_PLANNER_QUALIFICATION_SEARCH_DESIGN_INCOMPLETE`. The eight shifted targets do not establish bottle-family exhaustion.
- F2 r09/r10 both fail the same five preload hard checks: selected-finger continuity, unintended table contact, opening projection, reported rim-clearance pass, and 20 mm rim clearance. The old broad asset-exhaustion label is unsupported.

## Repaired CPU contracts

- F4: all three program orders now receive state-recursive OBB terminal and three-segment swept checks with 10 mm extra clearance. Eight new `hv2` layouts pass CPU geometry; none has planner or physical evidence.
- F3: 3,840 recipes cover 4 assets × 2 arms × 2 regions × 8 contacts × 10 rotations × 3 pregrasp distances. Region translation precedes final-pose freeze, and qualification/execution must match the final pose hashes.
- F2: 66/66 can/box pairs have collision-mesh/model/scale/orientation certificates; zero are runtime-qualified. New interfaces cover all contacts/rotations/heights, 5 mm/50 mrad post-close transform drift, explicit margin budgeting, actual-transform suffix construction, supported controlled insertion and five-step slow release. Ten-centimeter gravity drop is not primary.

## Verification and boundary

- Active focused: `17/17`; snapshot focused: `17/17`.
- Active full: `727/727` in 331.96 s; snapshot full: `727/727` in 308.01 s.
- Source: 272 Python files, byte-equal, SHA-256 `525d7666abbd77282caafb0fec5e4f823765284b8aeecba46ae954816d8f9bd6`.
- Tests: 136 Python files, byte-equal, SHA-256 `7f68b187d51f20f18de6fdab28f7ff8006fc1901f182eae9519aaa3badc3fdac`.
- Machine report SHA-256: `30f483ece98d06a6a199dfed28ed32606be2c64752e347364e8694c357295a2d`.

No GPU, planner, physical execution, trajectory, Stage 1, formal360, training, H-reveal, compression or π0.5 is authorized by this repair.
