# Mesh material provenance correction — CPU review

The frozen upright design described unchanged friction as 0.5/0.5 and added
that assertion. The actual create_actor mesh loader does not pass the scene's
declared physical material. SAPIEN's mesh builder uses get_default_material;
the pinned library's CPU read returns float32 0.3/0.3 and restitution 0.1.
No active task source sets that global default. These are distinct materials.

The last failed scene did not persist individual shape values before raising.
Therefore that scene's exact material list remains unrecorded, not fabricated
from this source review. A future run must save every actual shape material and
the loader default before checking them. Mismatch must still stop.

This proposal corrects a newly introduced provenance assertion; it must not
call a material setter or tune friction, mass, dynamics, numerical success
thresholds, or grasp design. The original design/failed terminal remain intact.
A new hash-bound metadata overlay must explicitly distinguish scene-declared
0.5/0.5 from unchanged mesh-loader 0.3/0.3. CPU tests do not authorize a new GPU
attempt or establish standing/grasp success.
