"""Source-only actual inheritance inventory; never imports the CUDA scene graph."""
import ast
from pathlib import Path
from .runtime import REQUIRED_METHODS

W = Path('/nfs_share/lijunhui')
A = W/'Vault-on-Fvl09/数据构造/实现审计'
P = W/'Robotwin2/project/RoboTwin/controlled_multi_future/probes'
SOURCES = {'Base_Task': W/'Robotwin2/project/RoboTwin/envs/_base_task.py',
           'AuditScene': P/'scene_inspection.py', 'F3Scene': P/'scene_inspection.py',
           'DenseTraceMixin': P/'runtime_trace.py'}


def class_node(name):
    tree = ast.parse(SOURCES[name].read_text(encoding='utf-8'))
    return next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)


def inventory():
    nodes = {name: class_node(name) for name in SOURCES}
    methods = {name: sorted(n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))) for name, node in nodes.items()}
    fields = {}
    for name, node in nodes.items():
        for fn in node.body:
            if isinstance(fn, ast.FunctionDef):
                for item in ast.walk(fn):
                    if isinstance(item, ast.Attribute) and isinstance(item.ctx, ast.Store) and isinstance(item.value, ast.Name) and item.value.id == 'self':
                        fields.setdefault(item.attr, []).append(name + '.' + fn.name)
    # Fail closed if the actual registry no longer composes DenseTraceMixin first.
    tree = ast.parse((P/'action_feasibility_v2.py').read_text(encoding='utf-8'))
    registry = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_scene_resources')
    f3_calls = [n for n in ast.walk(registry) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'type' and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == 'TraceF3RuntimeV2']
    if len(f3_calls) != 1 or ast.unparse(f3_calls[0].args[1]) != '(DenseTraceMixin, F3Scene)':
        raise ValueError('official trace F3 registry composition changed')
    if [ast.unparse(b) for b in nodes['F3Scene'].bases] != ['AuditScene'] or [ast.unparse(b) for b in nodes['AuditScene'].bases] != ['Base_Task']:
        raise ValueError('actual F3 inheritance changed')
    chain = ['DenseTraceMixin', 'F3Scene', 'AuditScene', 'Base_Task']
    providers = {method: next((name for name in chain if method in methods[name]), None) for method in REQUIRED_METHODS}
    if not all(providers.values()):
        raise ValueError('source method coverage missing')
    # Inventory all direct scene/s calls in the new qualification chain.
    callers = [A/'goal_pilot48_v1/f3_upright_qualification_runtime_v1'/f for f in ('runtime.py', 'ik.py', 'micro_binding.py', 'native.py')]
    callers += [A/'goal_pilot48_v1/f3_upright_hd_video_wrapper_v2/recorder.py', A/'goal_pilot48_v1/f3_runtime_v6/micro.py']
    usages = {}
    for path in callers:
        parsed = ast.parse(path.read_text(encoding='utf-8'))
        for n in ast.walk(parsed):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in ('scene', 's'):
                usages.setdefault(n.attr, set()).add(path.name + ':' + str(n.lineno))
    return {'official_mro': chain, 'required_method_providers': providers,
            'field_initializers': {k: sorted(set(v)) for k, v in sorted(fields.items())},
            'caller_scene_attributes': {k: sorted(v) for k, v in sorted(usages.items())},
            'scope': 'source structural interface audit; not a SAPIEN/physics test'}


def structural_classes():
    """Compile real class methods, suppress import-time annotations/default values only.

    Method bodies stay actual source; this does not import CUDA or construct scenes.
    """
    env = {'gym': type('Gym', (), {'Env': object})}
    for name in ('Base_Task', 'AuditScene', 'F3Scene', 'DenseTraceMixin'):
        node = class_node(name)
        node.decorator_list = []
        node.body = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for fn in node.body:
            fn.decorator_list = []
            fn.returns = None
            for arg in list(fn.args.posonlyargs) + list(fn.args.args) + list(fn.args.kwonlyargs):
                arg.annotation = None
            if fn.args.vararg: fn.args.vararg.annotation = None
            if fn.args.kwarg: fn.args.kwarg.annotation = None
            fn.args.defaults = [ast.Constant(None) for _ in fn.args.defaults]
            fn.args.kw_defaults = [ast.Constant(None) if x is not None else None for x in fn.args.kw_defaults]
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(SOURCES[name]), 'exec'), env)
    env['DenseTraceMixin'].trace_frequency_hz = 250
    return env
