# High-Level Template Redesign V1.2.5 CPU Freeze

Status: `CPU_SOURCE_SNAPSHOT_FROZEN_LEGACY_AND_SCENE_RENDER_PIN_GPU_DIAGNOSTIC_NOT_RUN`

- Active full suite: `707/707`, 246.948 s.
- Review-snapshot full suite: `707/707`, 246.081 s.
- Active/snapshot source: 268 Python files, byte-equal, tree/source SHA-256 `cf6fa611f7f6e234d484c1ab4fcb3774a70cb2bcadccf2293767f666b56ce927`.
- Active/snapshot tests: 132 Python files, byte-equal, tree SHA-256 `68b958ee2a32977a8ebc6e9c5829959dd0a223bbb62386a500649bf59ddb3255`.
- V1.2.5 parent authorization SHA-256: `5a9e923d6bd6c3aa038f5d731b7f4229dc23264210b427f282e26754b80950f8`.
- V1.2.5 registry SHA-256: `f58bef2b7d5bb6861ac2f5422cffa463fd97e5ea6893037786b5f2540a60c0cf`.
- Machine report SHA-256: `bc4c4bb37f7574f6de25eb98c5ef7a2ec673aa354f61e28e49be89fb5faeec24`.

Both SAPIEN contexts are now pinned inside the UUID-isolated child: the legacy pybind `SapienRenderer(Device("cuda:0"))` and the scene `RenderSystem(Device("cuda:0"))`. The binding receipt requires the legacy pin and the selected UUID/PCI to match the scene render-device PCI.

GPU validation has not run. The single-job full-PIDS diagnostic must be repeated before candidate requalification resumes. Stage 1, formal 360 collection, training, H-reveal, compression, and π0.5 remain unauthorized.
