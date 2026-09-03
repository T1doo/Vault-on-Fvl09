# PLANNER_WIRING_SMOKE_V1 Terminal Failure Review

Status: `TERMINAL_INFRASTRUCTURE_ERROR_BEFORE_PLANNER`

The exact Phase 1 wave was validly approved and S1 was validly issued, but the production Guard rejected the authorization before child launch. GPU3 was fresh-idle both immediately before the command and after it. No planner, scene, physical action, or trajectory ran.

The direct cause is an O_EXCL self-conflict. `gpu_guard_v2_4` creates the authorized Guard receipt first so failures remain auditable, then invokes the V2.3.1a authorization validator. That validator, with `allow_completed_paths=False`, rejects the already-created Guard receipt path. The same file that the Guard is required to claim therefore makes its authorization invalid.

The Guard terminal is `failed_authorization_binding` with code `96`. The immutable Guard receipt payload is `6f41bb84983d5e802503e9a7075989b6a56c3ba3c6634e2a908655e627840a76`. The S1 authorization was not consumed; no child, lease, cache, output namespace, stdout, or stderr was created.

The wave is permanently closed as `INFRASTRUCTURE_ERROR_STOPPED`. S2 through S7B were skipped. Aggregate usage is zero planner queries, zero scenes, zero physical executions, zero trajectories, and 22.6959 seconds of Guard validation.

Because the production normalizer assumes that a child outer terminal exists, an explicit administrative prevalidation terminal was used to close the ledger. It is clearly marked as not being child output and binds the immutable authorization and Guard evidence.

The next proposed Gate is `V2_3_1B_GUARD_PREVALIDATION_INTEGRATION_REPAIR`, limited to CPU/source work. It must preserve output O_EXCL, Guard immutability, single-use/no-retry behavior, all smoke budgets and scientific contracts, and add both a real Guard-main subprocess regression and a production pre-child failure terminalization API. Neither that repair nor a replacement smoke is authorized by this review.

Machine review SHA-256: `98a2c16c2692d3485613efb069a4c00b80a82dd00beb81ce8eb848a7c0be6471`

