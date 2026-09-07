import unittest
from unittest.mock import patch
from . import replace_unlaunched_upright_with_hd as replacement

class Tests(unittest.TestCase):
    def test_wrong_active_reservation_cannot_mutate_budget(self):
        with patch.object(replacement,'checked',return_value={'jobs':[{'job_id':replacement.OLD}]}), \
             patch.object(replacement.budget,'snapshot',return_value={'active_reservations':{}}), \
             patch.object(replacement.budget,'reconcile') as reconcile:
            with self.assertRaises(ValueError):
                replacement.main()
            reconcile.assert_not_called()

    def test_missing_video_or_launched_prior_blocks_before_cancellation(self):
        with patch.object(replacement,'checked',return_value={'jobs':[{'job_id':replacement.OLD}]}), \
             patch.object(replacement.budget,'snapshot',return_value={'active_reservations':{replacement.OLD:replacement.CAPS}}), \
             patch.object(replacement,'build_manifest',side_effect=ValueError('not ready or prior launched')), \
             patch.object(replacement.budget,'reconcile') as reconcile:
            with self.assertRaises(ValueError):
                replacement.main()
            reconcile.assert_not_called()

if __name__ == '__main__':
    unittest.main()
