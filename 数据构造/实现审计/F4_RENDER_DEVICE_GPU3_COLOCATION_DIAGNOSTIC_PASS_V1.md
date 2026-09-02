# F4 Render-Device GPU3 Co-location Diagnostic Pass V1

Status: `GPU3_SINGLE_CARD_RENDER_COMPUTE_PRESENTATION_COLOCATION_PASS`

The V1.2.6 single-job diagnostic selected physical GPU3. Mid-run full PIDS showed task PID 3199582 only on GPU3 as `C+G` (525 MiB); no nonselected GPU contained the task PID. The in-process binding receipt independently matched selected UUID `GPU-d5b84492-…` and PCI `0000:61:00.0` to the actual scene render device.

The r01 candidate completed all 42 planner queries, all Stage-B Gates passed, physical execution remained zero, and Guard cleanup returned GPU3 to 15 MiB/0%/P8 with no task process.

On this host, F4 SAPIEN jobs must therefore run serially on fresh-idle physical GPU3. This is a scheduler constraint, not a new GPU authorization allowlist: authorizations remain GPU0–7, but GPU3 is the only currently audited device that co-locates CUDA/render/presentation on one card.

Machine report SHA-256: `878ec9e1497a373a8ecfa85e8e35865e15c72fe84fc8baf3e90125af172ac88a`.
