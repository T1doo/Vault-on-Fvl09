"""Only an actually accepted B root can supply these three motion cells."""
from copy import deepcopy
from pathlib import Path
from ..f4_b_program_runtime_v1.runtime import bound_json
from ..f4_b_root_runtime_v1.runtime import prerequisites as root_prerequisites
from ..f4_b_root_runtime_v1.entry import disk_finalizer
from ..f4_b_runtime_v1.binding import seal,PROGRAMS
from ..runtime.issue_f4_b_stage_a import sha,read,W

def root_inputs(job):
    goal=bound_json(job,'source_root_goal_terminal');guard=bound_json(job,'source_root_guard_terminal')
    manifest=bound_json(job,'source_root_manifest','manifest_sha256');runtime=goal.get('runtime_result') or {}
    if (goal.get('pass') is not True or goal.get('accounting_complete') is not True or
        goal.get('resource_counts')!=dict(solver_problems=460,fresh_scenes=11,action_scenes=7,collection_attempts=3) or
        runtime.get('development_root_pass') is not True or runtime.get('finalizer',{}).get('accepted') is not True or
        guard.get('child_exit_code')!=0 or guard.get('task_owned_cleanup_pass') is not True or
        guard.get('manifest_sha256')!=manifest['manifest_sha256'] or goal.get('manifest_sha256')!=manifest['manifest_sha256'] or
        manifest['jobs'][0].get('runtime_module')!='goal_pilot48_v1.f4_b_root_runtime_v1.runtime'):
        raise ValueError('accepted real B root/Guard/finalizer required')
    parent_output=Path(manifest['jobs'][0]['output_namespace']).resolve()
    if not parent_output.is_relative_to(W/'Robotwin2/datasets') or not parent_output.name.startswith('p48_f4_b_root_'):
        raise ValueError('only a new B root namespace is permitted, never F4-A')
    bound=root_prerequisites(manifest['jobs'][0]);root=parent_output/'development_root'
    if read(root/'root_receipt.json')!=runtime['root_receipt']:raise ValueError('B root disk/Goal receipt mismatch')
    proof=disk_finalizer(dict(root_receipt=runtime['root_receipt'],development_root_pass=True,
        development_accepted_root_count=1,development_accepted_trajectory_count=3),manifest['jobs'][0],parent_output)
    if proof.get('accepted') is not True:raise ValueError('B root current disk raw/video/verifier audit failed')
    return root,bound,runtime['root_receipt']

def catalog(root,bound,root_receipt):
    root=Path(root);frozen=read(root/'candidate_frozen_root_spec.json')
    if frozen['planned_root_slot_spec']!=bound['planned_spec']:raise ValueError('B frozen scene differs')
    if [p['program_id'] for p in frozen['programs']]!=list(PROGRAMS):raise ValueError('three B candidates required')
    dependencies={};cells=[]
    for name in ('root_receipt.json','candidate_frozen_root_spec.json','planned_root_slot_spec.json','reference_current_hashes.json','reference_anchor.json',
                 'canonical_prefix_artifact/canonical_prefix_artifact.json','canonical_prefix_artifact/prefix_arrays.npz'):
        path=root/name;dependencies[str(path)]=sha(path)
    for program in frozen['programs']:
        pid=program['program_id'];suffix=root/'suffix_artifacts'/pid/'frozen_suffix_artifact.json'
        source=read(suffix);targets=deepcopy(source['execution_spec']['targets'])
        changed=[i for i,t in enumerate(targets) if t['segment_id'].endswith('_carry_mid')]
        if len(targets)!=30 or len(changed)!=3:raise ValueError('original F4 three carry-mid targets required')
        branch=root/'branches'/pid/'receipt.json';disk=read(branch)
        if disk!=next(r for r in root_receipt['branch_receipts'] if r['program_id']==pid) or disk['status']!='accepted':raise ValueError('B source branch incomplete')
        cell=dict(cell_id='F4_B_motion__'+pid,family='F4',cohort='F4_B_motion',program=program,
            parent_root=str(root),parent_root_id=bound['planned_spec']['slot_id'],variant='r_inv_motion',
            candidate_universe_sha256=frozen['candidate_universe_sha256'],source_suffix=str(suffix),source_suffix_file_sha256=sha(suffix),
            source_branch=str(branch),source_branch_file_sha256=sha(branch),targets=targets,changed_indices=changed,
            query_cap=0,scene_cap=1,attempt_cap=1,motion_uses_frozen_parent_controls=True,nominal_duration_scale=1.10)
        cells.append(cell)
        files=[suffix,suffix.parent/'suffix_controls.npz',branch,branch.parent/'trace_source.npz',branch.parent/'video/trajectory.mp4']
        files += [branch.parent/'raw'/name for name in ('raw_streams.npz','manifest.json','manifest.sha256.json')]
        for path in files:dependencies[str(path)]=sha(path)
    return seal(dict(schema_version='cmf_B_motion_three_cells_v1',cells=cells,dependencies=dependencies,new_independent_root_count=0))
