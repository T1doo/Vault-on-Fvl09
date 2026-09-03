# PLANNER_WIRING_SMOKE_V1 Wave Approval V2

- Wave: `planner-wiring-smoke-v1-20260903-run1`
- Status: `APPROVED_FOR_EXACT_PHASE1_SMOKE_ONLY`
- User evidence: after Phase 0 was sealed and the next exact Gate was stated as the 152-query wiring smoke, the user instructed `请继续！`.
- Machine approval: `PLANNER_WIRING_SMOKE_V1_WAVE_APPROVAL_V2.json`
- Approval payload SHA-256: `6b6e36cb577e21a70636092d690c8f512f1930c3c590de7908683089ddde813f`
- Activation contract SHA-256: `5d6baaba2ae07ec3b3ab5511b3a80caf2c0a24474de4d627ac5adf6bfd6333d0`
- Smoke proposal SHA-256: `36b6bac57fb6c7cceb6f7fc35858c1cb25492cd2106b662d878a4a475d01b801`
- Manifest bundle SHA-256: `31fde740b4b7a19257375429f2afeb4e17cbaffb5f98a440eb4e7214e390f041`
- Runtime implementation SHA-256: `62245cb3a36ee1d4b6b70a5192db35cf9115bc44ef7fa6f29878125252d62109`
- Source freeze Vault commit: `a9ee20c74a522120182009897ede5c0f12e6fc40`
- Official RoboTwin tracked commit: `c3ddfa8b97d5519efa828b075999bd0006778e5e`

The exact aggregate ceiling is 152 planner queries, 9 fresh scenes, 16,200 seconds, zero physical execution, and zero trajectories. Jobs are serial and single-use; candidate failure is terminal evidence, while any infrastructure error closes the wave. Conditional slots are issued only from validated immutable predecessor terminals.

The authorization correctly retains `allowed_physical_gpu_indices=[0,1,2,3,4,5,6,7]`. On this host the whole single-GPU wave is scheduled only on fresh-idle physical GPU3 because existing full-PIDS evidence has validated F4 compute/render/presentation co-location only there.

This approval does not authorize the 1,696-query full panel, physical execution, Stage 1, formal 360 collection, training, H-reveal, compression, or π0.5. The run must stop and publish a terminal review when this smoke wave ends.
