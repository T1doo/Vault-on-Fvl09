# F4 Render-Device Diagnostic V1 Failure

Status: `EXPLICIT_RENDER_SYSTEM_PIN_INCOMPLETE_LEGACY_RENDERER_CROSS_CARD`

The single-job V1.2.4 diagnostic selected physical GPU0. Mid-run full PIDS showed child PID 3154872 as `C+G` on GPU0 (399 MiB) and simultaneously `G` on nonselected physical GPU3 (4 MiB).

V1.2.4 correctly pinned the scene `RenderSystem`, but RoboTwin `Base_Task.setup_scene` first constructs the legacy wrapper `sapien.core.SapienRenderer()`. In SAPIEN 3.0.0b1 that wrapper ignores device keyword arguments and initializes a separate default renderer context. This remaining context selected GPU3.

The diagnostic was immediately interrupted. The Guard preserved an uncertain signal-boundary receipt, while targeted `ps` and full PIDS afterward confirmed the task PID absent and GPU0/GPU3 returned to baseline. No candidate conclusion, physical execution, or trajectory was produced.

Machine report SHA-256: `a74b02994ba09384f4cd9aefe3f9a98b239eff2318ca1ed5e9ac8f8d0e17870e`.

The next version must pin both the legacy `SapienRenderer` and the scene `RenderSystem` to logical `cuda:0`, then repeat the same single-job full-PIDS diagnostic.
