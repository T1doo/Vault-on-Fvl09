# High-Level Template Redesign V1.2.6 CPU Freeze

Status: `CPU_SOURCE_SNAPSHOT_FROZEN_UNUSED_LEGACY_RENDERER_SUPPRESSED_GPU_DIAGNOSTIC_NOT_RUN`

- Active full suite: `707/707`, 246.366 s.
- Review-snapshot full suite: `707/707`, 245.694 s.
- Active/snapshot source: 268 Python files, byte-equal, tree/source SHA-256 `bd4fc1f1c9b7be60300012352a20751bb6b7509dff8e8f20c6790aa8c72eee25`.
- Active/snapshot tests: 132 Python files, byte-equal, tree SHA-256 `ccbe38de2dad62c6fdd55798b8089c31f9c32152490311d1a381c7e5e641f6b1`.
- V1.2.6 parent authorization SHA-256: `ef730364a46a2c6de90844ed09c93ad58bd7f190e464f50e4f33fcf96b2691cf`.
- V1.2.6 registry SHA-256: `6e0084575d605fc89554b453fa0787b7289ee6eeb65a74a8ead22731a1098d09`.
- Machine report SHA-256: `eff579128db9c9a7f9ef58872c57135d4df281ba6b0e70b5abad4be992d5d85a`.

The frozen F4 scene uses `render_freq=0`; the unused legacy `SapienRenderer` is now suppressed completely. The only renderer-related GPU object is the scene `RenderSystem(Device("cuda:0"))`, whose PCI must match the Guard-selected UUID/PCI.

GPU validation has not run. A third single-job full-PIDS diagnostic is required before candidate requalification resumes. Stage 1, formal 360 collection, training, H-reveal, compression, and π0.5 remain unauthorized.
