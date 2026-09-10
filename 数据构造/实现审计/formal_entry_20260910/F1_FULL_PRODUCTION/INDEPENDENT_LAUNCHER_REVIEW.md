# Independent launcher/recovery review

Scope: read-only second-pass review of first_wave_launcher.py, execution_cli.py, test_launcher_recovery.py and test_launcher_real_pipeline.py, including the native reuse boundary they call. No launcher source edits, GPU snapshots, leases or native physical runs were performed by this reviewer.

## Positive checks directly inspected

- GPU authorization and source/spec validation precede host snapshots and lease acquisition.
- Acquisition has a separately persisted UUID/host/monotonic start record. Child terminal, cleanup, lease release/end and measured duration precede usage parsing and ledger settlement.
- Unknown release or owned cleanup retains the reservation and leaves ended/lease_seconds unknown. Recovery does not replace missing timing with the current clock or the reservation cap.
- Physical counters use cumulative native receipts minus the saved baseline; only the new lease duration is added. Existing successful raw/manifests/capture hashes are checked before reuse. Ledger settlement uses an idempotency key.
- Resume requires a classified failure, completed resource reconciliation, compatible source/spec, a distinct bounded attempt and the remaining shared/root budget. Repeating a completed recovery request does not invoke a new backend.
- The explicit copy-only path rechecks real disk acceptance and copies after GPU release; it does not construct a backend, take a GPU snapshot or reserve a lease. A separate integration test exercises actual CLI/finalizer/export/copy with only the simulator boundary replaced and checks preserved raw bytes.
- Busy-before-child produces DEFERRED_READY and zero physical attempt consumption. Independent fresh-card checks and per-root UUID continuity remain in place.

## Concrete findings sent to implementation owners

1. HostBackend.run's exception handler wrote child_end.json again before terminating/reaping owned processes. If that write failed again, cleanup was skipped. Cleanup must be in a finally path independent of evidence-write success.
2. The outer lease-finalization block wrote lease_release.json before lease_terminal.json. A failure of the former suppressed the already measured release-end/duration record. Terminal persistence must be attempted independently (or first), so a secondary audit-file error cannot erase timing.
3. The backend call was marked child_launched before Popen. If the backend explicitly returned launched=false/pid=null, the marker was not corrected; known no-child startup failures could consume the physical-attempt count. Unknown child state should remain conservative, but known absence should be represented accurately.
4. The native recovery interface accepted reviewed source amendments at its upper levels, but deeper prefix reuse still required the original planner-source/full-current hashes and the old strict physics_config metadata comparison. A real CMF source amendment changes those provenance hashes even when actual arrays and physical state match. The native owner was asked to bridge only the explicitly reviewed provenance differences while retaining exact effective-prefix arrays, model-visible/physical current checks and original raw/artifact bytes.

## Review evidence and status

The inspected tests cover measured timing after acquisition failures, post-snapshot failure, usage-parser failure, settle failure, unconfirmed release, coordinator restart, busy/no-child behavior, bounded retry, repeated commands, source/spec mismatch and actual saved-file copy-only recovery. Reading these tests is not presented as independently executing their final revised version.

CLOSED_AFTER_FROZEN_DIFF_AND_TARGETED_CPU_RECHECK. This review adds no new Guard, scheduler or approval framework. The four findings were rechecked against the actual corrected source and the targeted runs below. Synthetic backend tests remain nonphysical and cannot count toward the future 90 trajectories.

## Final independent recheck

1. HostBackend now uses a non-throwing evidence helper and performs owned terminate/reap in finally. The injected child_end write-failure test confirms the known owned process is still signalled and waited for.
2. lease_terminal is attempted before lease_release, each persistence attempt is independent, and a persistence-error record retains the measured terminal as a backup. The injected release-log write failure retains an integer measured duration and settles without leaking the reservation.
3. A backend's explicit launched=false now clears child_launched before attempt accounting. An additional independent CPU backend run confirmed physical_attempts=0 and collection_attempts=0; its failure status remains explicit rather than pretending collection succeeded.
4. Source-only recovery now has an explicit comparison view. Direct source inspection confirms it changes only the approved implementation_source_sha256 and hashes derived from that provenance. Persisted current/capture/anchor originals keep their real source identity; model-visible hashes, hidden-physical hashes, numeric poses/joints and other physical configuration fields are preserved. Planner source transitions require the reviewed receipt, and regenerated effective-prefix arrays still compare byte-for-byte before old artifact reuse. The real launcher/CLI source-amendment fixture completes with its accepted original cell bytes preserved.

Independent command executed after source freeze:

`PYTHONDONTWRITEBYTECODE=1 /nfs_share/lijunhui/Robotwin2/env/bin/python -m unittest test_launcher_recovery.PersistenceFinalizersTests test_launcher_real_pipeline.SourceCompatibilityPipelineTests -v`

Result: 3 tests passed in 31.070 seconds. The additional known-no-child CPU run passed separately. Host process APIs and simulator boundaries were replaced by explicit fixtures; no actual GPU was initialized and no real trajectory was added. The broader final-family suite is recorded in the coordinator's separate final logs and is not represented as independently rerun here.

Reviewed file hashes at closure:

- first_wave_launcher.py: `9fcab411264ba02a2615e1a9954cc1a03adf329886922aba73cad5c26ba370a2`
- execution_cli.py: `7b19ac14086fc33145dd1003a0ff1472504d20cdb307c4a2bb41d0242bce019b`
- native_f1.py: `70689946b33ece33fe120ddcbf62ffa5e77c5ffd3c552e53a34e6b8cde5ccead`
- native_f1_orchestrator.py: `287e9b938d44977923eb47b66b18a971dd4ec18d3050fb3855c2ce1f5fb703a8`
