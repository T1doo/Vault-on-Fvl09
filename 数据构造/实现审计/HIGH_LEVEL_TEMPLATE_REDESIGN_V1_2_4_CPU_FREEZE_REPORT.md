# High-Level Template Redesign V1.2.4 CPU Freeze

Status: `CPU_SOURCE_SNAPSHOT_FROZEN_EXPLICIT_RENDER_PIN_GPU_DIAGNOSTIC_NOT_RUN`

- Active full suite: `707/707`, 246.769 s.
- Review-snapshot full suite: `707/707`, 246.355 s.
- Active/snapshot source: 268 Python files, byte-equal, tree/source SHA-256 `202ba7cba388fb7d18684be60a90f13c69178a8212bb3cc281b97a09719a6c4f`.
- Active/snapshot tests: 132 Python files, byte-equal, tree SHA-256 `8fae277b0d8bfad8bb2cafa1f97f705705ed25f41844dbea5b9a8edb3bdc4979`.
- V1.2.4 parent authorization SHA-256: `9fdb84267372014ad7005a2f0da53301a1e86b27572469472eaea54d54cbaa6f`.
- V1.2.4 registry SHA-256: `3f236365d7e933b561a7adf96e536ed02186da12ec0e309ccc591d25d844a044`.
- Machine report SHA-256: `e510d221cd3d387602dd9ab53746bb79c06bfea385a5fe6836e82ec2c0f7de4e`.

F4 scene construction now explicitly creates `RenderSystem(Device("cuda:0"))` inside the Guard's UUID-isolated child. It queries the selected physical index/UUID/PCI mapping and requires the actual render-device PCI identity to match before scene use. The binding is stored in each candidate receipt.

GPU validation has not run yet. One single-job full-PIDS diagnostic must pass before any parallel candidate wave. Stage 1, formal 360 collection, training, H-reveal, compression, and π0.5 remain unauthorized.
