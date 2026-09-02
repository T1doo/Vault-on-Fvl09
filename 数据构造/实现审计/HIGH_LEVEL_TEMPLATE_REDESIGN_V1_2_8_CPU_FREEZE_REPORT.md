# High-Level Template Redesign V1.2.8 CPU Freeze

Status: `CPU_SOURCE_SNAPSHOT_FROZEN_F4_A_ONLY_ARM_BINDING_REPLACEMENT_READY`

- Active full suite: `710/710`, 527.32 s.
- Review-snapshot full suite: `710/710`, 527.21 s.
- Active/snapshot source: 268 Python files, byte-equal, tree/source SHA-256 `a594759ac140eae6d0dc248f5da930f909f39c91065e4f7e7a7cdc3c8918e23c`.
- Active/snapshot tests: 132 Python files, byte-equal, tree SHA-256 `aff9c99bacb4c761d845af36dde33626049cb929410e686dce45f3055610c149`.
- Parent authorization SHA-256: `e7b4e11872d9b866ee4d28ec58bbd3ff511e07b931373f950482b13fc6a26278`.
- Registry SHA-256: `aaf47bfc01990b27cf815dc101b5ae3e2c4ab2b420f496c15083c1564ef0f9ec`.
- Machine report SHA-256: `ddbb74097cc72ccf4a40c46c9f002f9c84da6737ee348013855b8c7574d5ff21`.

V1.2.8 fixes only the V1.2.7 A-only common-prefix arm routing error. The common-X target-construction scope now explicitly binds the frozen right-arm grasp contract even though the selected A branch uses the left arm. The override is rejected outside `common_x_route_repair`; ordinary full-program arm inheritance is unchanged. Candidate set/rank, layout, target geometry, verifier thresholds, planner budget, physical-attempt budget, and Stage-A/Stage-B selections are unchanged.

Two initial focused-test invocations failed before any test body ran because the unittest module path and then the working-directory-relative path were wrong. The corrected focused suites passed, followed by both complete 710-test suites. No GPU was used for this freeze.

The V1.2.7 run1 authorization remains consumed and immutable. The next safe step is one fresh V1.2.8 selected-r01 A-only replacement scope, executed serially on fresh-idle physical GPU3. Stage 1, formal collection, training, H-reveal, compression, and π0.5 remain unauthorized.
