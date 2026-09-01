# High-Level Template Redesign V1.2.1 CPU Freeze

Status: `CPU_SOURCE_SNAPSHOT_FROZEN_STAGE_B_BUDGET_CORRECTED_GPU_NOT_RUN`

- Active full suite: `705/705`, 263.611 s.
- Review-snapshot full suite: `705/705`, 262.499 s.
- Active/snapshot source: 268 Python files, byte-equal, tree/source SHA-256 `a99ee9919639c65f278f8d9969e420816f78e9ada73b8fc181d781cc89e9e86a`.
- Active/snapshot tests: 132 Python files, byte-equal, tree SHA-256 `a042520aa9ea4f61d654ebfb51f3ba1499bd481c8a46454f7f12ba66a4f5a0f0`.
- V1.2.1 parent authorization SHA-256: `e159fc8f6971de48d6c53ad5db2aa42180e68f9c8d66fd6d18c729273eca16ee`.
- V1.2.1 registry SHA-256: `bf71a4a718e862d10262fdfd1c0b37a8ca4c089bf1261a451293943a4c4f9e98`.
- Machine report SHA-256: `af5773110b6b91857e38d93d9dcde10d19f42797c62ea16a00bad12ef373722b`.

The only runtime correction is the F4 Stage-B planner-query limit: `32 → 33`. The selected left-arm source deterministically performs three official grasp-target batch queries plus thirty chain-segment queries. Candidates, rank, targets, physical-execution count, Gates, thresholds, and selection rules are unchanged.

Run1 remains superseded and must not be reused. This freeze does not authorize Stage 1, formal 360 collection, training, H-reveal, compression, or π0.5.
