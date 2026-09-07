"""Restore the official trace-capable F3 base without modifying frozen sources."""
import ast
import inspect
import types
from goal_pilot48_v1.f3_upright_qualification_runtime_v1 import context
from goal_pilot48_v1.f3_upright_bootstrap_recovery_v1.runtime import Counts
from goal_pilot48_v1.f3_upright_hd_video_wrapper_v2 import runtime as hd

REQUIRED_METHODS = ('_contacts', 'initialize_trace', '_record', 'mark', 'save_trace',
                    'take_dense_action', '_reserve_planner_query', 'selected_gripper_links',
                    'finish_development_video_capture', 'setup_demo', 'load_actors',
                    '_update_render', 'close_env', 'move')


def require_trace_base(base):
    missing = [name for name in REQUIRED_METHODS if not callable(getattr(base, name, None))]
    if missing or getattr(base, 'trace_frequency_hz', None) != 250:
        raise ValueError('official F3 trace capability missing: ' + repr(missing))
    return base


def compiled_make():
    tree = ast.parse(inspect.getsource(context.make))
    class Bind(ast.NodeTransformer):
        count = 0
        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) and node.func.id == 'make_scene_class':
                if node.keywords or len(node.args) != 1:
                    raise ValueError('frozen scene factory signature changed')
                self.count += 1
                selected = ast.parse("_require_trace_base(_scene_resources()[0]['F3'])", mode='eval').body
                node.keywords = [ast.keyword(arg='base_class', value=selected)]
            return self.generic_visit(node)
    bind = Bind()
    tree = bind.visit(tree)
    if bind.count != 1:
        raise ValueError('exact one upright scene factory required')
    env = dict(context.__dict__)
    env['_require_trace_base'] = require_trace_base
    exec(compile(ast.fix_missing_locations(tree), __file__, 'exec'), env)
    return env['make']


def private_hd_runner(meter):
    base = types.ModuleType('private_upright_official_trace_base')
    base.__dict__.update(hd.base.__dict__)
    base.Counts = lambda: Counts(meter)
    base.make = compiled_make()
    env = dict(hd.__dict__)
    env['base'] = base
    return types.FunctionType(hd.run.__code__, env)


def run(manifest, *, meter):
    if (manifest.get('trace_recovery_of') != 'p48_f3_upright_qualification_bootstrap_001'
            or manifest.get('failed_setup_scene_count_retained') != 2
            or manifest.get('new_finite_recovery_scope') is not True
            or manifest.get('second_successful_confirmation_not_authorized_here') is not True):
        raise ValueError('new finite recovery scope retaining both failed scenes required')
    return private_hd_runner(meter)(manifest, meter=meter)
