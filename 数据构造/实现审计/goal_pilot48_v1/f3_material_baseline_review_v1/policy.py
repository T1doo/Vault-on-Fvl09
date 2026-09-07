"""Validate unchanged mesh-loader material, never set physics parameters."""
import ast
from pathlib import Path
import numpy as np

W = Path('/nfs_share/lijunhui')
FACTORY = W/'Robotwin2/project/RoboTwin/envs/utils/create_actor.py'
BUILDER = W/'Robotwin2/env/lib/python3.10/site-packages/sapien/wrapper/actor_builder.py'
EXPECTED = [float(np.float32(.3)), float(np.float32(.3)), float(np.float32(.1))]

def verify_loader_route():
    tree = ast.parse(FACTORY.read_text(encoding='utf-8'))
    fn = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='create_actor')
    calls = [n for n in ast.walk(fn) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
             and n.func.attr=='add_multiple_convex_collisions_from_file']
    if len(calls)!=1 or any(k.arg=='material' or k.arg is None for k in calls[0].keywords):
        raise ValueError('mesh material creation route changed')
    tree = ast.parse(BUILDER.read_text(encoding='utf-8'))
    fn = next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='add_multiple_convex_collisions_from_file')
    if not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='get_default_material' for n in ast.walk(fn)):
        raise ValueError('default-material route not found')

def material_values(material):
    return [float(material.get_static_friction()),float(material.get_dynamic_friction()),float(material.get_restitution())]

def validate_values(actual, default):
    if list(default)!=EXPECTED:
        raise ValueError('installed mesh default differs from reviewed baseline')
    return bool(actual and all(list(v)==EXPECTED for v in actual))

def capture(scene):
    import sapien
    from controlled_multi_future.probes.runtime_trace import _entity
    verify_loader_route()
    actual = []
    for component in _entity(scene.bottle).get_components():
        if hasattr(component,'get_collision_shapes'):
            for shape in component.get_collision_shapes():
                actual.append(material_values(shape.get_physical_material()))
    default = material_values(sapien.physx.get_default_material())
    error = None
    try:
        valid = validate_values(actual,default)
    except ValueError as exc:
        valid = False
        error = str(exc)
    return {'actual_shape_materials':actual,'mesh_loader_default':default,
            'expected_unchanged_mesh_material':EXPECTED,
            'scene_declared_default_is_a_distinct_material':[.5,.5,0.],
            'pass':valid,'validation_error':error,'physical_material_written':False}
