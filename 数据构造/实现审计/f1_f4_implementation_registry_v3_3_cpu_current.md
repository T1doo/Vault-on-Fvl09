# F1–F4 implementation registry：runtime-v3_3 revision-9 CPU current

| Family | revision-8实现 | Envelope | 状态 |
|---|---|---:|---|
| F1 | revision-2 root保持accepted | 46/3/0 historical | `accepted_nonformal_root` |
| F2 | r8 fixed XY + r9 mean-aperture balanced-preload、inside/support/disengagement-before-full-open | 32/3/0 | `r9_cpu_ready_not_run` |
| F3 | physical signal + diagnosis final-first + balance→fixed +0.16 slow disengagement-before-full-open | 96/3/0 | `r9_cpu_ready_not_run` |
| F4 | r8 top-down staged/full + r9 NumPy JSON-safe canonicalization | 118/7/0 | `r9_cpu_ready_not_run` |

F4 A-only micro仍是accepted nonroot Gate；完整roots仍1/4。Active/snapshot各427/427、diff零；source=`f76c013aebbe98d705dc62f77a83c47fdefbc899d0818e84b489639b1cd95d21`，budget=`56b5d18115e5c0f7d24738ab49909633f26a69fd8e4b2b6235952f1c4751687f`。Revision-9 bundles/GPU尚不存在；先发布clean baseline，Stage0仍禁止。
