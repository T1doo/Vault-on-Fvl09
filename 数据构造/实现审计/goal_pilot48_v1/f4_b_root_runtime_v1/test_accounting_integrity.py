"""CPU-only ledger corruption fixtures; not generated trajectories."""
from types import SimpleNamespace
import unittest
from .accounting import count_queries

class Tests(unittest.TestCase):
    def test_duplicate_missing_reordered_or_boolean_ids_rejected(self):
        for ids in ([1,1],[1,3],[2,1],[True,2],[1,None]):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                count_queries(SimpleNamespace(planner_query_count=2,
                    planner_queries=[{'query_id':i} for i in ids]))

    def test_replayed_provenance_does_not_disrupt_actual_sequence(self):
        scene=SimpleNamespace(planner_query_count=2,planner_queries=[
            {'query_id':1},{'query_id':15,'replayed_from_frozen_suffix_artifact':True},
            {'query_id':2}])
        result=count_queries(scene)
        self.assertEqual(result['solver_problems'],2)
        self.assertEqual(result['replayed_query_rows'],1)

    def test_noninteger_or_unrecognized_batch_metadata_rejected(self):
        cases=[{'query_id':1,'batch_size':10},
               {'query_id':1,'query_type':'batched_grasp_target_selection',
                'batch_size':10.0,'ordered_goal_poses':[[0]*7]*10},None]
        for row in cases:
            with self.subTest(row=row), self.assertRaises(ValueError):
                count_queries(SimpleNamespace(planner_query_count=1,planner_queries=[row]))

if __name__=='__main__':unittest.main()
