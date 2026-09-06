"""Private v1 execution globals plus one private live geometry height adapter."""
import ast,hashlib
from pathlib import Path
from .contract import A,build_contract,manifest_lineage,proposal
from goal_pilot48_v1.f2_inward_runtime_v2.runtime import load_private_runtime as parent_private

def live_target_helper():
    from semantic_target import OLD_PATH,OLD_SHA,old
    if hashlib.sha256(OLD_PATH.read_bytes()).hexdigest()!=OLD_SHA:raise ValueError('frozen target derivation changed')
    text=OLD_PATH.read_text(encoding='utf-8');tree=ast.parse(text)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_derive_live_targets')
    source=ast.get_source_segment(text,node)
    xy='expected[:2] = candidate_xy';height='preplace = world_axis_offset_pose(release, 0.08)'
    if source.count(xy)!=1 or source.count(height)!=1:raise ValueError('unexpected frozen target function')
    source=source.replace(xy,'# compensated actor origin remains untouched')
    source=source.replace(height,'preplace = world_axis_offset_pose(release, ROUTE_APPROACH_HEIGHT)')
    ns=dict(old.__dict__);ns['ROUTE_APPROACH_HEIGHT']=proposal()['new_approach_height_m']
    exec(compile(source,str(OLD_PATH)+':private_U_route_revision1','exec'),ns)
    def derive(scene,contract):return ns['_derive_live_targets'](scene,contract,'beside')
    return derive

def load_private_runtime(manifest):
    private=parent_private(manifest)
    original_dependencies=private.dependencies
    def dependencies():
        panel=original_dependencies() # this loader already creates an unregistered private module
        panel.derive_live_targets=live_target_helper()
        return panel
    def bound_contract():
        c=build_contract();fields=manifest_lineage(c)
        if any(manifest.get(k)!=v for k,v in fields.items()):raise ValueError('manifest does not bind fixed-layout route revision1')
        from realization_utf8_io_v1 import write_new
        out=Path(manifest['jobs'][0]['output_namespace'])
        write_new(out/'runtime_route_revision1_lineage.json',{'schema_version':'f2_route_revision1_private_runtime_v3',
          'lineage':fields,'binding':c['binding'],'planned':c['planned'],'goals':c['inward_goals'],
          'all_three_endpoints_require_fresh_model_checks':True,'parent_D_success_not_used_to_skip_checks':True,
          'layout_and_seed_unchanged':True,'shared_module_globals_modified':False})
        return c
    private.dependencies=dependencies;private.build_contract=bound_contract;return private

def run(manifest):return load_private_runtime(manifest).run(manifest)
