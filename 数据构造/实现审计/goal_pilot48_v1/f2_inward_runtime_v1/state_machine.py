"""CPU-testable route sequencing; no simulator or CUDA imports."""
import numpy as np

class Budget:
    def __init__(self):
        self.ik = 0
        self.trajectory = 0

    def reserve(self, kind):
        cap = {'ik': 3, 'trajectory': 4}[kind]
        value = getattr(self, kind)
        if value >= cap:
            raise ValueError(kind + ' cap exhausted')
        setattr(self, kind, value + 1)
        return value + 1

def open_named_qpos(full_qpos, names, gripper_mapping, scale):
    q = np.asarray(full_qpos, dtype=np.float32).copy()
    if len(names) != len(q) or len(set(names)) != len(names):
        raise ValueError('invalid full joint mapping')
    if not gripper_mapping:
        raise ValueError('missing actual gripper mapping')
    changes = {}
    for name, multiplier, offset in gripper_mapping:
        if name not in names or name in changes:
            raise ValueError('gripper name missing/duplicate')
        # Exact Robot.set_gripper target formula at normalized open = 1.
        value = float(scale[1]) * float(multiplier) + float(offset)
        q[names.index(name)] = value
        changes[name] = float(q[names.index(name)])
    return q, changes

def run_route(initial_qpos, goals, *, endpoints_pass, budget, plan, merge, screen, release):
    if not endpoints_pass:
        return {'pass': False, 'reason': 'ENDPOINT_GATE_FAILED', 'segments': [], 'transition': None}
    q = np.asarray(initial_qpos, dtype=np.float32).copy()
    rows = []
    transition = None
    for i, key in enumerate(('U_new', 'D_new', 'U_new', 'N')):
        ordinal = budget.reserve('trajectory')
        before = q.copy()
        control = plan(goals[key], before, ordinal)
        row = {'ordinal': ordinal, 'goal': key, 'state': 'carry' if i < 2 else 'released', 'start_qpos': before.tolist(), 'planner_pass': control.get('status') == 'Success', 'executed': False}
        rows.append(row)
        if not row['planner_pass']:
            return {'pass': False, 'reason': 'PLANNER_FAILED', 'segments': rows, 'transition': transition}
        checks = screen(control, i)
        row['geometry_screen'] = checks
        if not checks['pass']:
            return {'pass': False, 'reason': 'NATIVE_GEOMETRY_SCREEN_FAILED', 'segments': rows, 'transition': transition}
        q = np.asarray(merge(before, control['position'][-1]), dtype=np.float32)
        row['end_qpos'] = q.tolist()
        if i == 1:
            q, transition = release(q.copy())
            q = np.asarray(q, dtype=np.float32)
            if not transition['pass'] or transition.get('attached_can_present') is not False or transition.get('released_can_present') is not True:
                return {'pass': False, 'reason': 'RELEASE_TRANSITION_FAILED', 'segments': rows, 'transition': transition}
    return {'pass': True, 'reason': 'FOUR_SEGMENT_PLANNER_ONLY_PASS', 'segments': rows, 'transition': transition, 'terminal_qpos': q.tolist()}
