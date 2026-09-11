# F1_000013 attempt6 authorization request

CPU-only gates are complete for a new candidate package. No GPU lease has been acquired.

- manifest contract: `11be9b26496f19ab47b5daf5976a9779339b8f0aafee684c172809ad87ba831d`
- source bundle: `62e73b7b065828d34a6af74c1739040eba1ea135a9822512a78c788310511817`
- fixed GPU: `GPU-2c620e6c-9639-2022-b573-9847dfa33769`
- scope: three `r_inv_motion` cells only
- prior consumed: fresh/action/collection/solver/GPU lease = `9/4/0/0/645`
- reservation: fresh/action/collection/solver/GPU lease = `11/7/3/64/6555`
- `accepted_cells`: 6/6 verified before GPU
- attempt6 is one-shot; attempt7 will not auto-start

To continue, explicitly authorize this candidate's physical execution. Without that authorization the candidate remains CPU-only.
