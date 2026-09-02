# F4 Render-Device Diagnostic V3 GPU0 Failure

Status: `GPU0_SINGLE_CARD_GATE_FAIL_FIXED_PRESENTATION_GPU3_HYPOTHESIS`

V1.2.6 suppressed the unused legacy renderer and retained only the explicitly selected scene `RenderSystem`, yet the GPU0 diagnostic still showed task PID 3194271 on GPU0 (`C+G`, 475 MiB) and GPU3 (`G`, 4 MiB).

This rules out the unused legacy renderer as the source of the remaining tiny context. The current evidence-based hypothesis is a fixed host/SAPIEN display or presentation context on physical GPU3. The next diagnostic uses the same frozen source but selects physical GPU3; if compute, render, and presentation co-locate there and no other card shows the task PID, the one-root/one-card rule can be satisfied by serial GPU3 execution.

The GPU0 diagnostic was interrupted and cleaned up; no candidate conclusion, physical execution, or trajectory was produced.

Machine report SHA-256: `22689d44f328a0a24d87e49cf8775b6982039e40c63958fed26c5f261ba281e4`.
