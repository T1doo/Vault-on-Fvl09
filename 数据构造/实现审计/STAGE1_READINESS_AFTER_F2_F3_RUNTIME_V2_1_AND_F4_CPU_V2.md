# Stage 1 Readiness after F2/F3 Runtime V2.1 and F4 CPU V2

Date: 2026-09-04
Status: `NOT_READY_F1_R_INV_INCOMPLETE_F2_ROUTE_GATE_INFRASTRUCTURE_FAILED_F3_SHARED_V_PHYSICAL_FAILED_F4_ROOT_AWAITING_EXTERNAL_APPROVAL`

## Unified counts

| Scope | Accepted roots | Accepted trajectories | Target | Authorized |
|---|---:|---:|---:|---|
| Development | 5 | 15 | not a formal denominator | only previously authorized F1 `r_pc` work completed |
| Canonical Stage 1 | not promoted/countable | 0 | 48 trajectories | false |
| Formal | 0 | 0 | 40 roots / 360 trajectories | false |

All five accepted development roots and all 15 accepted development trajectories are F1 `r_pc`. F2, F3, and F4 each remain at `0 roots / 0 trajectories`. Diagnostic traces, debug MP4s, planner receipts, physical-isolation passes, and Stage 0 data are not counted as accepted development or formal trajectories.

Stage 0 remains immutably sealed as `STAGE0_COMPLETED_WITH_FAILURE_EVIDENCE`: 12 active slots, 15 historical terminal attempts, 5 successes, 7 failures, 5 raw trajectories, 5 required MP4s, and 0 formal roots. It is not reopened by this readiness update.

## Family status

| Family | Implemented | Generated | Verified | Scientifically supported | Accepted development | Remaining Gate |
|---|---|---|---|---|---:|---|
| F1 | Runtime implemented and exercised | 5 roots / 15 `r_pc`; 15 raw + 15 MP4 | 5/5 roots and 15/15 branches passed same-current, anchor, raw, video, and family verification | F1 development `r_pc` construction only; no claim for real invariance, 9/9 atomic completion, Stage 1, or formal data | 5 / 15 | Explicitly authorize and collect real `r_inv_path` and `r_inv_motion`, then satisfy root-atomic 9/9; no automatic promotion |
| F2 | 11-query route Gate and read-only post-run auditor implemented and CPU-validated | Latest run produced only failure/cleanup receipts; 0 planner, physical, raw, video, or root outputs | Verified NVRTC infrastructure failure before planner and verified clean GPU/process/cache/lease release | No controlled-route scientific result is available | 0 / 0 | External review must first approve a versioned path-only recovery using cache `/nfs_share/lijunhui/Robotwin2/cache/f2` and the resulting 82-character TMPDIR, then rerun the unchanged 5-inside + 6-beside Gate; current one-shot is consumed and third dispatch is false |
| F3 | V2.1 executed; pre-close physical-consistency Gate implemented and CPU replay-validated | Four physical failure traces and four debug MP4s; 0 raw/root trajectories; no-suffix scenes 0 | Stage A/B 3/3 passed; physical 0/4; accounting 58 queries / 10 scenes; new Gate tests 20/20 and rejects all four sealed traces before close | Negative result and root cause are supported: CuRobo approximate collision feasibility diverges from SAPIEN self/table/pad contact physics; gripper logic, action layout and verifier are not the primary fault | 0 / 0 | External review must approve the Gate design and a deterministic freeze rule for four new candidates before any bounded 25 mm micro-lift requalification; at least two physical passes remain required before no-suffix |
| F4 | Runtime V2.1 CPU final hardening implemented | Current V2.1 runtime generated no production output; preserved evidence is diagnostic/template evidence only | CPU finalizer 18/18, environment 21/21, lineage 5/5, executable identity 3/3, and POST_CHILD 11/11 pass; historical isolation 5/5 and full-program template 3/3 pass | Physical template is qualified, but no accepted root or root-runtime execution is verified | 0 / 0 | Obtain a new external decision, specifically `APPROVE_ONE_F4_INFRASTRUCTURE_CORRECTED_ROOT_V2`; until then proposal V2 remains `approved=false` and all F4 execution authorities are false |

F1's exact preserved evidence has two separate roles. The sealed Stage 0 F1 root passed 3/3 and produced three raw trajectories and three MP4s. The later development batch separately passed 5/5 roots and 15/15 `r_pc` trajectories. Neither may be reclassified as Stage 1 or formal data.

The F4 proposal preserves the externally frozen manifest field `root_status=INFRASTRUCTURE_FINAL_HARDENING_REQUIRED`. The later CPU review demonstrates that this hardening was implemented and tested. Therefore the current operational interpretation is `HARDENING_COMPLETE_AWAITING_EXTERNAL_APPROVAL`, without rewriting the proposal or implying execution authority.

## Authorization boundary

The following all remain false:

- Stage 0 reopen or rerun;
- canonical Stage 1;
- formal 360 collection;
- training;
- H-reveal;
- compression;
- π0.5;
- F1 promotion or new invariance collection;
- F2 automatic retry, third dispatch, or automatic root transition;
- F3 additional/second reissue, no-suffix continuation, or root execution;
- F4 approval, GPU, planner, scene, physical, root execution, or automatic continuation.

## Bound evidence

- F1: `F1_BATCH_GENERATION_PILOT_V1_REPORT.json`, report `dd3d371c54b7abe3b3f54d511a4c848d3262ec67f858e4829456d9a7f92b166c`, evidence commit `41af8b884e1cb0dc353d0134de213d883edd9a77`.
- Stage 0: result receipt `394093a2571269eaa659cc90df654c449ffd1fb3a9ab041bbcfc321231c21df7`, terminal seal `08ef2c20e6508b32a026fcd168ce5b69bb8686cec0071e5a243d7e211e810783`, evidence commit `dc9e70c2c22ce152d7c926bdf8c9b93c8bc443b3`.
- F2: terminal publication receipt `bc28ef29817dd522d15a5379aba914f46445b11b494eb41c361cbb6c98ff8ff7`, evidence commit `86ee8cd40441d4a36329b37291dbe6f9ca64b729`.
- F3: terminal publication receipt `070e1bec9e46e2b5aa42c8e489fd168d073be78b77cd2d14f61a8fbc74016210`, evidence commit/current input HEAD `be2ce89c1fc06bb2797f8f22323bc3c033066df5`.
- F3 pre-close CPU review: receipt `2c9910fdbf3ceb94bae8415e84a93e31e9520d1673c07e4d22df32db36643ae3`; proposal manifest `1ef3f9b543b4f93cdbccf5948d3022c1116456d04a8dd0d5bf12cdf1c6115b1e`; all execution authority remains false.
- F4: proposal manifest `ea27ac315516b2006a96bd92594e125473970d111d2ef12434be9fecc11893e5`, prepublication receipt `a585de409f4fb857ee14cf8499335e697946359457b10892d60abf5405a3f5a9`, CPU review receipt `f1efa1fa8e093a2ca900171cab9cd72d1fb1f44f5ffbca2fff398aa58a1db166`, runtime source commit `10d4ec85a02e4d0bf47bee65d7022bb46f6aa98b`, publication commit `de5f57a6db6805d63d8e62cb8e803f98bbdae1cd`.

The companion JSON is the machine-readable authority for exact fields and carries a canonical self-hash.
