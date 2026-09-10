# F1 anchor equivalence and independent semantic copies

CPU-only implementation; no GPU, scenes, re-collection, historical migration or source deletion.

## One physical equivalence rule

`anchor_equivalence.py` freezes `f1_physical_anchor_equivalence_v1` for physical_anchor_v2 at fresh t0. Its field whitelist includes robot qpos/qvel/drive targets, four actual gripper joints, dynamic role pose/linear/angular velocity/sleep state, facility poses, physics configuration, source commit and metadata. Missing/nonfinite fields, wrong dimensions, extra undefined physical fields, wrong root/spec/source binding and role-set changes fail. The 76-entry repeated articulation representation is accepted only when its two 38-entry halves are exactly equal.

The rule preserves the existing execution comparator tolerances: 1e-6 per native joint coordinate/velocity, 1e-6 m position norm, 1e-6 rad orientation, 1e-6 m/s and rad/s velocity components. Quaternion sign is ignored and orientation normalized as in the original comparator. The rule records frame, phase, units and exact metadata. This is the fresh-anchor contract, not the 3 mm task-terminal non-task gate. Native generalized coordinates retain their original revolute-radian/prismatic-meter units; no numerical normalization or cross-unit comparison is introduced.

Identity is supplied by each actual capture: root_id, spec_sha256 and source_bundle_sha256. Both hashes must be valid and identical across the root by default. An explicitly CPU-reviewed source-compatibility receipt may bind the exact old/new source bundle pair for the same root/spec, only for old capture hashes listed in accepted_cells. The same receipt may map physics_config.implementation_source_sha256 from its declared old code SHA to its declared new code SHA. Every other physical/configuration field retains the original equality/tolerance rule; the original capture and anchor are never rewritten. The receipt itself is indexed and copied as source_compatibility evidence. Native capture/root validation and copied root validation consume the same helper. Every original anchor is retained; JSON whitespace and float textual representation are not physical identity. The helper, rule JSON and reader are included in the copied package. Reading never falls back to origins.

Single-file integrity remains strict SHA256 against the sealed source index. Cross-cell RGB/state and strict r_pc prefix comparisons operate on decoded values (NPZ key set, dtype, shape and exact array bytes), rather than compressed archive bytes. Anchor equivalence uses the physical rule. A compression/JSON formatting difference is therefore accepted without weakening single-file integrity.

## Publication API and layout

`f1_portable_export.copy_root(index, destination, *, fault=None, registry_path=None, expected_index_sha256=None)` verifies the frozen index and sources, copies actual files, then calls `portable_v2.publish_root`. Pass the known sealed index SHA through expected_index_sha256; a mismatch stops before copy.

The destination is the intended `.../releases/formal_v1/F1/F1_XXXXXX/`. It contains:

- group_manifest.json and a byte-equivalent root_manifest.json compatibility entry;
- common/reader.py, common/anchor_equivalence.py and common/anchor_contract.json;
- intent01_red/, intent02_green/, intent03_blue/ (names derived from structured candidates);
- under each intent, r_pc/, r_inv_path/ and r_inv_motion/ with independently retained actual captures, supervision, native provenance and raw evidence.

`portable_v2.read_root(root)` verifies the group, common rules, all nine nested packages, their actual 3×3 identity, current arrays, physical anchors and three r_pc prefixes. It returns the group entry. FAMILY_MANIFEST.json and dataset_index.csv remain the coordinator's responsibility; the entry provides root_id, family, cells, relative_cell_paths and candidates. No physical eligibility is inferred merely from copying or fixture acceptance.

## Recovery and original preservation

Each root has its own lock and unique staging directory/journal. Verified staged files are reused; partial files are completed and hash-checked before atomic rename. Published roots are re-read before idempotent registry repair. Source/spec/version conflicts refuse overwrite. The short registry lock protects registration; unrelated root copies can proceed independently.

Supported fault hooks: cell_copy_mid, root_copy_mid, rename_pre, rename_post and index. Copy-only recovery reruns copy_root with the same sealed index and destination. It does not invoke a collector, construct scenes, reset attempts or alter original data. Successful intermediate cell packages remain independent physical files; storage budgeting includes those copies and retained failed staging. Same-NFS copies support independent access and accidental-deletion recovery, not hardware/offsite backup.

## Targeted evidence

`test_anchor_copy_v1.py` exercises equivalent JSON representations, duplicate articulation storage, allowed 0.5 µm actor displacement, rejected 2 µm displacement, missing state, wrong root/spec/source, nonfinite fields, changed rules, replaced source bytes, compressed/uncompressed NPZ equivalence, full semantic-root publication, all root-copy interruption boundaries, idempotent recovery and source-disabled bundled reading. Original source hashes are rechecked unchanged.

Existing portable and generic formal-export tests are also retained. Full F1 native lifecycle integration is coordinated with the collector owner after the new capture bindings and per-cell gates are frozen; the final command/result is reported by the central validation record.

Source-only compatibility targeted tests cover approval absence, exact old/new bundle mapping, accepted old capture binding, unchanged numerical physics configuration, and rejection when dt changes despite an approval receipt. This exception was coordinated with the execution/recovery and independent-review owners; it is not a generic metadata ignore rule.
