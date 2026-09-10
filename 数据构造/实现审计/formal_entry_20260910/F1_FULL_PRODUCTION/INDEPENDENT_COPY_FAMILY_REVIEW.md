# Second-pass read-only review: family completion and copy integration

Reviewer: portable/anchor implementation agent, reviewing the coordinator-owned `f1_full_production.py` and its launcher call boundary. No launcher/family scheduler edits were made by this reviewer. This is a targeted independent code review, not a rerun of GPU experiments.

## Findings reported before coordinator revisions

1. `make_job` used the whole source-bundle JSON hash as `implementation_source_sha256`, while the native adapter compares against the CMF relative-path/content streaming digest. Those algorithms differ; real native construction would reject the package. Coordinator reports this corrected; final source diff still needs confirmation.
2. The first compatibility validation call used family state_dir, while prior launcher jobs live in state_dir/launcher/STATE.json. Coordinator reports this corrected; final diff pending.
3. Family failure-resolution lookup read the job_proofs wrapper rather than its receipt field. Coordinator reports nested lookup corrected; final diff pending.
4. `_activation_jobs` regenerated reserve files using the original source map during a reviewed source-only recovery, while launcher compatibility initially recognized only the ten primary jobs. Existing and newly activated reserve jobs need coherent reviewed source bindings; coordinator and launcher owner are addressing this.
5. `verify_completed_job` read nine individual packages but did not call `portable_v2.read_root`; that misses common-rule integrity and cross-cell anchor equivalence at final publication. Launcher owner was asked to use the full root reader before registry comparison.
6. Final family publication checked zero reservations but did not recheck selected job status, settled usage, owned cleanup/release on the COMPLETE restart branch, or reject a known budget overrun. Coordinator is correcting the final gate.
7. Package validation did not constrain first-wave roots, concurrency fields, duplicate/incorrect job IDs or unique raw/copy destinations. A malformed job-ID map can route the wrong root before later identity checks reject it. Coordinator is tightening the schema.
8. Family state/storage checks used lexical absolute paths and a leaf symlink check. An ancestor symlink could escape the workspace. Coordinator is switching to the existing safe-origin checker.

## Positive findings

The barrier/reserve logic assigns replacements by original primary rank, not worker finish order. A persisted activation barrier is reused after restart; the initial and remaining barriers are separate. The normal loop does not mark 90 complete from ten arbitrary directory entries: selected originals/replacements and ninety unique cell keys are checked. The first phase currently waits for the first root terminal before dispatching the second root, a conservative scheduling choice that does not bypass the first-cell acceptance requirement.

The new copy implementation validates every original source file against its sealed index; preserves each actual anchor; distinguishes decoded-array/physical equivalence from file SHA identity; and stores reader/rules and semantic intent/realization paths in each independent root. This review does not self-certify those agent-owned changes; they are assigned to a different reviewer for cross-check.

## Status

CODE_FINDINGS_CLOSED_AFTER_DIRECT_DIFF_RECHECK. The reviewer re-read the actual corrections described below. Final frozen end-to-end regression commands and hashes remain the coordinator's validation record; this status does not claim GPU validation. No GPU, planner, renderer or native physical execution was performed for this review.

## Follow-up read after coordinator changes

The revised source now computes the native CMF digest separately, uses launcher state for compatibility, reads nested failure-resolution receipts, validates the stronger job/phase/path schema, preserves previously generated reserve authorizations and reads the append-only ledger for final resource totals. Those changes were directly read, not inferred from an acknowledgement.

Two additional boundary cases were reported for correction:

9. A reserve that is already activated in FAMILY_STATE but has never been dispatched lacks a launcher bound_job record. Its source amendment must receive the persisted activated_jobs explicitly; otherwise a valid reserve compatibility job is rejected before the family state is loaded.
10. Final publication must validate each accepted_by_primary mapping against the original primary or the reserve activation proof. Ten unique roots plus aggregate split/difficulty counts alone do not reject swapped primary/reserve lineage.

The final family manifest should also distinguish original contract source from each selected root's effective source/compatibility lineage, rather than presenting one original source hash as though it described every recovered cell. Final closure remains pending the last coordinator/launcher diff and frozen regressions.

## Final direct-diff recheck

The final reviewed source closes the ten reported code findings:

- make_job calls the separate native implementation digest; complete dependency source pins remain distinct.
- The family entry safely reads matching FAMILY_STATE first and passes activated_jobs to compatibility validation at state_dir/launcher. Nested failure-resolution proofs are consumed correctly.
- Reserve job creation preserves existing jobs and uses reviewed source overrides for newly activated jobs; immutable activation proofs and source-specific config subdirectories are retained.
- verify_completed_job now calls portable_v2.read_root before checking the root/registry/execution-result bindings.
- Final publication rechecks selected PASS records, settled attempts, owned cleanup and release, and reads/hash-validates actual ExecutionLedgerV2 totals, rejecting reservations and overrun.
- Package schema binds ten exact job IDs, the first two train roots, concurrency, root budgets and unique/expected raw and copy destinations; safe origin checks cover ancestor symlinks.
- Each selected result must match its primary split/difficulty, and replacements must carry the exact primary-root activation proof. The coordinator added a swapped-medium-primary negative case to the full-family test.
- FAMILY_MANIFEST now labels the original contract source separately and records each selected authorization source/compatibility lineage.

No additional completion-gate blocker was found in this bounded final read. The first18→remaining72 barrier, reserve restart identity, complete90 count, physical-resource final gate and separate F1-only boundary are represented in the actual call chain. This conclusion is about source correctness within the inspected scope; full frozen CPU integration and future native physics remain separate evidence.
