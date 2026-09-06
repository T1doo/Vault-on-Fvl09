"""B-specific constructor; reuse original scene lifecycle and family operations."""
from .binding import validate_runtime, PROGRAMS

def make_adapter(*, output_root, source_sha256, planned_spec, full_program_specs=None):
    # Imports instantiate no Scene or CUDA; creation remains the caller's Guard scope.
    from controlled_multi_future.real_sapien_adapter_high_level_v1 import RoboTwinRealSapienF4HierarchicalStageAV1Adapter
    from controlled_multi_future.real_sapien_adapter_f4_selected_layout_v2 import RoboTwinRealSapienF4SelectedLayoutV2Adapter
    from controlled_multi_future.real_sapien_adapter_f4_qualified_root_v1 import RoboTwinRealSapienF4QualifiedDevelopmentRootV1Adapter
    from controlled_multi_future.f4_full_program_physical_v1 import validate_f4_full_program_physical_spec_v1
    base = RoboTwinRealSapienF4HierarchicalStageAV1Adapter if full_program_specs is None else RoboTwinRealSapienF4QualifiedDevelopmentRootV1Adapter
    class BoundBAdapter(base):
        def __init__(self):
            self.planned_spec = validate_runtime(planned_spec)
            self.f4_candidate = self.planned_spec['f4_source_grasp_candidate_v1']
            RoboTwinRealSapienF4SelectedLayoutV2Adapter.__init__(self, family='F4', output_root=output_root,
                expected_implementation_source_sha256=source_sha256)
            if full_program_specs is not None:
                if set(full_program_specs) != set(PROGRAMS):
                    raise ValueError('three B program specs required')
                values = {pid: validate_f4_full_program_physical_spec_v1(v) for pid,v in full_program_specs.items()}
                for pid, value in values.items():
                    if (value['program_id'] != pid or value['legacy_scene_spec'] != self.planned_spec or
                        value['candidate_sha256'] != self.planned_spec['f4_stage_b_candidate_sha256']):
                        raise ValueError('adapter received A/mixed B full-program specs')
                if len({v['isolation_gate_receipt_sha256'] for v in values.values()}) != 1:
                    raise ValueError('mixed isolation lineage')
                self.full_program_specs = values
    return BoundBAdapter()
