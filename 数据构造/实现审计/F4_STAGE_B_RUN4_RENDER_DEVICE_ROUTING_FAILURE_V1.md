# F4 Stage-B Run4 Render-Device Routing Failure

Status: `R03_R04_CANDIDATE_FAILURE_R05_R06_SAFETY_ABORT_R07_R08_UNCONSUMED`

- r03/r04 are valid candidate failures: both passed six A-role segments and failed at `A_preplace`; physical execution remained zero and both Guards cleaned up normally.
- During r05 on selected physical GPU0, `nvidia-smi -q -d PIDS` showed the r05 child PID 2711682 holding a 4 MiB Vulkan/graphics context on physical GPU3. CUDA UUID binding alone did not bind SAPIEN's default `RenderSystem`.
- r06 had already entered GPU3 when the cross-card graphics context was identified. Both task-owned Guard sessions were interrupted to restore the one-job-per-card/root-not-cross-card boundary.
- The Guards recorded cleanup uncertain at the signal boundary, but a subsequent targeted privileged `ps` confirmed both child PIDs absent, and GPU0/GPU3 returned to 14/15 MiB, 0%, P8 with no task processes. The original Guard receipts remain immutable.
- r07/r08 remained unconsumed with no Guard or output.

Machine report SHA-256: `22d9715f2c1c5727b00ca8723f9fec99968c81373743cfd93f89efa178615390`.

Before more GPU work, SAPIEN rendering must be explicitly pinned to logical `cuda:0` inside the UUID-isolated child, and the resulting render-device PCI identity must be audited against the selected physical GPU UUID/PCI mapping.
