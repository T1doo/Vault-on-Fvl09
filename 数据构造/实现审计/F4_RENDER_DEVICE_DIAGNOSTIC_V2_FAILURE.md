# F4 Render-Device Diagnostic V2 Failure

Status: `LEGACY_AND_SCENE_DEVICE_PIN_STILL_CROSS_CARD_GLOBAL_OR_LEGACY_CONTEXT`

V1.2.5 pinned both the legacy pybind `SapienRenderer` and the scene `RenderSystem` to logical `cuda:0`, but the single-job full-PIDS diagnostic still showed the task PID on selected GPU0 (`C+G`, 399 MiB) and nonselected GPU3 (`G`, 4 MiB).

The frozen scene configuration uses `render_freq=0`; the legacy renderer object is not used by cameras or a viewer. Therefore the next correction will suppress legacy `SapienRenderer` construction entirely while retaining the explicitly pinned scene `RenderSystem`. It will hard-gate `render_freq=0` and repeat the same full-PIDS diagnostic.

The failed diagnostic was interrupted immediately. Targeted `ps` and full PIDS confirmed the task PID absent and both GPUs returned to baseline. No candidate conclusion, physical execution, or trajectory was produced.

Machine report SHA-256: `090c29d1f156cfc05bb83a6a01a3eed93a89d6cf5abfd8dd211e7775752a4f3d`.
