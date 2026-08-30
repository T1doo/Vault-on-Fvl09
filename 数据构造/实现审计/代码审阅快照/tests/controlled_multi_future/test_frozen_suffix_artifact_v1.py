import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from controlled_multi_future.canonical_prefix_artifact_v1 import (
    canonical_json_sha256,
)
from controlled_multi_future.current_hasher import hash_array
from controlled_multi_future.f3_return_release_v5 import (
    transform_f3_return_controls_v5,
)

from controlled_multi_future.frozen_suffix_artifact_v1 import (
    build_frozen_suffix_artifact,
    load_frozen_suffix_artifact,
    validate_frozen_suffix_artifact,
    write_frozen_suffix_artifact,
)


def artifact():
    controls = [
        {
            "status": "Success",
            "position": np.arange(18, dtype=np.float32).reshape(3, 6),
            "velocity": np.ones((3, 6), dtype=np.float32),
            "_cmf_planner_query": {
                "query_id": 1,
                "arm": "left",
                "source": "s0",
                "goal_eef_pose": [0, 0, 0.9, 1, 0, 0, 0],
                "status": "Success",
                "start_step": None,
                "end_step": None,
            },
        },
        {
            "status": "Success",
            "position": np.arange(12, dtype=np.float32).reshape(2, 6),
            "velocity": np.full((2, 6), 0.5, dtype=np.float32),
            "_cmf_planner_query": {
                "query_id": 2,
                "arm": "left",
                "source": "s1",
                "goal_eef_pose": [0, 0, 1.0, 1, 0, 0, 0],
                "status": "Success",
                "start_step": None,
                "end_step": None,
            },
        },
    ]
    spec = {
        "program_id": "F1-red",
        "actual_prefix_end_qpos_sha256": hash_array(
            np.zeros(7, dtype=np.float64)
        ),
        "control_cache_key": "transient",
        "targets": [
            {"segment_id": "s0", "pose": [0, 0, 0.9, 1, 0, 0, 0]},
            {"segment_id": "s1", "pose": [0, 0, 1.0, 1, 0, 0, 0]},
        ],
        "segment_receipts": [
            {
                "segment_id": "s0",
                "planner_status": "Success",
                "start_qpos_sha256": "0" * 64,
                "end_qpos_sha256": "1" * 64,
            },
            {
                "segment_id": "s1",
                "planner_status": "Success",
                "start_qpos_sha256": "1" * 64,
                "end_qpos_sha256": "2" * 64,
            },
        ],
    }
    return build_frozen_suffix_artifact(
        root_slot_id="root-1",
        family="F1",
        program_id="F1-red",
        candidate_universe_sha256="a" * 64,
        prefix_artifact_sha256="b" * 64,
        actual_prefix_end_qpos=np.zeros(7),
        execution_spec=spec,
        controls=controls,
        planner_query_receipts=[{"query_id": 1, "status": "Success"}],
    )


class FrozenSuffixArtifactV1Test(unittest.TestCase):
    def test_roundtrip_preserves_control_arrays_without_cache_handle(self):
        manifest, arrays = artifact()
        self.assertNotIn("control_cache_key", manifest["execution_spec"])
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        output = Path(directory.name) / "suffix"
        write_frozen_suffix_artifact(output, manifest, arrays)
        loaded, _, controls = load_frozen_suffix_artifact(output)
        self.assertEqual(loaded["artifact_sha256"], manifest["artifact_sha256"])
        self.assertEqual(len(controls), 2)
        np.testing.assert_array_equal(
            controls[0]["position"], np.arange(18, dtype=np.float32).reshape(3, 6)
        )
        self.assertEqual(controls[0]["_cmf_planner_query"]["query_id"], 1)

    def test_control_tamper_fails(self):
        manifest, arrays = artifact()
        changed = dict(arrays)
        changed["segment_000_position"] = arrays["segment_000_position"].copy()
        changed["segment_000_position"][0, 0] += 1.0
        with self.assertRaisesRegex(ValueError, "array hash|segment hash"):
            validate_frozen_suffix_artifact(manifest, changed)

    def test_failed_control_cannot_be_frozen(self):
        manifest, arrays = artifact()
        bad = [
            {
                "status": "Fail",
                "position": np.zeros((1, 6), dtype=np.float32),
                "velocity": np.zeros((1, 6), dtype=np.float32),
            }
        ]
        with self.assertRaisesRegex(ValueError, "not successful"):
            build_frozen_suffix_artifact(
                root_slot_id="root-1",
                family="F1",
                program_id="F1-red",
                candidate_universe_sha256="a" * 64,
                prefix_artifact_sha256="b" * 64,
                actual_prefix_end_qpos=np.zeros(7),
                execution_spec={
                    "program_id": "F1-red",
                    "actual_prefix_end_qpos_sha256": hash_array(
                        np.zeros(7, dtype=np.float64)
                    ),
                    "targets": [
                        {
                            "segment_id": "s0",
                            "pose": [0, 0, 0.9, 1, 0, 0, 0],
                        }
                    ],
                    "segment_receipts": [
                        {
                            "segment_id": "s0",
                            "planner_status": "Fail",
                        }
                    ],
                },
                controls=bad,
                planner_query_receipts=[],
            )

    def test_f3_transformed_control_provenance_links_to_frozen_arrays(self):
        targets = [
            {
                "segment_id": "f3_return_preplace",
                "pose": [0, 0, 0.9, 1, 0, 0, 0],
            },
            {
                "segment_id": "f3_return_release",
                "pose": [0, 0, 0.8, 1, 0, 0, 0],
            },
        ]
        raw = []
        for index in range(2):
            raw.append(
                {
                    "status": "Success",
                    "position": np.arange(
                        24, dtype=np.float32
                    ).reshape(4, 6),
                    "velocity": np.ones((4, 6), dtype=np.float32),
                    "_cmf_planner_query": {
                        "query_id": index + 1,
                        "arm": "left",
                        "source": targets[index]["segment_id"],
                        "status": "Success",
                    },
                }
            )
        controls, transforms = transform_f3_return_controls_v5(raw, targets)
        qpos = np.zeros(7, dtype=np.float64)
        spec = {
            "program_id": "F3-VVHH",
            "actual_prefix_end_qpos_sha256": hash_array(qpos),
            "targets": targets,
            "execution_control_transforms": transforms,
            "segment_receipts": [
                {
                    "segment_id": item["segment_id"],
                    "planner_status": "Success",
                }
                for item in targets
            ],
        }
        manifest, arrays = build_frozen_suffix_artifact(
            root_slot_id="f3-root",
            family="F3",
            program_id="F3-VVHH",
            candidate_universe_sha256="a" * 64,
            prefix_artifact_sha256="b" * 64,
            actual_prefix_end_qpos=qpos,
            execution_spec=spec,
            controls=controls,
            planner_query_receipts=[],
        )
        validate_frozen_suffix_artifact(manifest, arrays)
        tampered = json.loads(json.dumps(manifest))
        tampered["segments"][0]["planner_query"][
            "execution_control_transform"
        ] = tampered["segments"][1]["planner_query"][
            "execution_control_transform"
        ]
        unsigned = dict(tampered)
        unsigned.pop("artifact_sha256")
        tampered["artifact_sha256"] = canonical_json_sha256(unsigned)
        with self.assertRaisesRegex(ValueError, "provenance"):
            validate_frozen_suffix_artifact(tampered, arrays)


if __name__ == "__main__":
    unittest.main()
