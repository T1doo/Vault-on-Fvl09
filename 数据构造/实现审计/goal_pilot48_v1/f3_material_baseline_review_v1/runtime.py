"""Material provenance assertion repair, with no physics setters."""
import ast
import inspect
import types
from pathlib import Path
from . import policy
from goal_pilot48_v1.f3_upright_trace_recovery_v1.runtime import compiled_make, Counts, hd
from realization_utf8_io_v1 import write_new

def corrected_spec(manifest):
    original = hd.base.read_spec(manifest)
    result = dict(original)
    parent = result.pop('receipt_sha256')
    result['parent_design_receipt_sha256'] = parent
    result['original_friction_metadata_preserved'] = original['friction_unchanged']
    result['friction_unchanged'] = dict(static=policy.EXPECTED[0],dynamic=policy.EXPECTED[1])
    result['mesh_restitution_unchanged'] = policy.EXPECTED[2]
    result['material_metadata_correction_only'] = True
    result['material_source'] = 'create_actor material omitted -> ActorBuilder physx.get_default_material'
    result['receipt_sha256'] = hd.base.hash_value(result)
    return result

def snapshot_with_material_record(output):
    def verify(scene):
        result = policy.capture(scene)
        result['receipt_sha256'] = hd.base.hash_value(result)
        write_new(Path(output)/'actual_material_baseline.json',result)
        if not result['pass']:
            raise ValueError('actual mesh material does not match unchanged loader baseline')
    tree = ast.parse(inspect.getsource(hd.base.snapshot))
    class Replace(ast.NodeTransformer):
        count = 0
        def visit_If(self,node):
            if (len(node.body)==1 and isinstance(node.body[0],ast.Raise)
                    and isinstance(node.body[0].exc,ast.Call)
                    and any(isinstance(a,ast.Constant) and a.value=='actual bottle material changed' for a in node.body[0].exc.args)):
                self.count += 1
                return ast.Expr(value=ast.Call(func=ast.Name(id='_record_and_check_material',ctx=ast.Load()),args=[ast.Name(id='scene',ctx=ast.Load())],keywords=[]))
            return self.generic_visit(node)
    replace = Replace()
    tree = replace.visit(tree)
    if replace.count!=1:
        raise ValueError('exact old material assertion not found')
    env = dict(hd.base.__dict__)
    env['_record_and_check_material'] = verify
    exec(compile(ast.fix_missing_locations(tree),__file__,'exec'),env)
    return env[tree.body[0].name]

def private_runner(manifest,meter):
    base = types.ModuleType('private_f3_material_metadata_correction')
    base.__dict__.update(hd.base.__dict__)
    base.Counts = lambda: Counts(meter)
    base.make = compiled_make()
    base.read_spec = corrected_spec
    base.snapshot = snapshot_with_material_record(manifest['jobs'][0]['output_namespace'])
    env = dict(hd.__dict__)
    env['base'] = base
    return types.FunctionType(hd.run.__code__,env)

def run(manifest,*,meter):
    if (manifest.get('material_metadata_recovery_of')!='p48_f3_upright_qualification_trace_001'
            or manifest.get('physical_material_change_authorized') is not False
            or manifest.get('failed_setup_scene_count_retained')!=3):
        raise ValueError('exact material provenance repair scope required')
    return private_runner(manifest,meter)(manifest,meter=meter)
