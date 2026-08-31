import unittest
from unittest.mock import patch

from controlled_multi_future.f1_batch_generation_pilot_v1 import (
    IMPLEMENTATION_VERSION as F1_IMPLEMENTATION,
)
from controlled_multi_future.f4_layout_candidate_search_v2 import (
    IMPLEMENTATION_VERSION as F4_IMPLEMENTATION,
)
from controlled_multi_future.f2_dynamic_development_scope_v3 import (
    IMPLEMENTATION_VERSION as F2_IMPLEMENTATION,
)
from controlled_multi_future.probes import gpu_guard_v2_4


class NewFamilyGuardDispatchV1Test(unittest.TestCase):
    def _exercise(self, implementation, loader_name, consumer_name, validator_name):
        authorization = {"implementation_version": implementation}
        with patch.object(
            gpu_guard_v2_4,
            "_authorization_implementation",
            return_value=implementation,
        ), patch.object(
            gpu_guard_v2_4, loader_name, return_value="loaded"
        ) as loader:
            self.assertEqual(
                gpu_guard_v2_4._load_runtime_authorization(
                    "unused", requested_scope="scope"
                ),
                "loaded",
            )
            loader.assert_called_once()
        with patch.object(
            gpu_guard_v2_4, consumer_name, return_value="consumed"
        ) as consumer:
            self.assertEqual(
                gpu_guard_v2_4._consume_runtime_authorization(
                    authorization, ledger_directory="unused"
                ),
                "consumed",
            )
            consumer.assert_called_once()
        with patch.object(
            gpu_guard_v2_4, validator_name, return_value="validated"
        ) as validator:
            self.assertEqual(
                gpu_guard_v2_4._validate_runtime_consumption(
                    "consumption", authorization
                ),
                "validated",
            )
            validator.assert_called_once()

    def test_f1_batch_dispatch(self):
        self._exercise(
            F1_IMPLEMENTATION,
            "load_f1_batch_pilot_v1",
            "consume_f1_batch_pilot_v1",
            "validate_f1_batch_pilot_consumption_v1",
        )

    def test_f4_selected_layout_dispatch(self):
        self._exercise(
            F4_IMPLEMENTATION,
            "load_f4_selected_layout_v2",
            "consume_f4_selected_layout_v2",
            "validate_f4_selected_layout_consumption_v2",
        )

    def test_f2_dynamic_development_dispatch(self):
        self._exercise(
            F2_IMPLEMENTATION,
            "load_f2_dynamic_development_v3",
            "consume_f2_dynamic_development_v3",
            "validate_f2_dynamic_development_consumption_v3",
        )


if __name__ == "__main__":
    unittest.main()
