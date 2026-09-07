"""Direct bridges to unchanged original inside gate implementations."""
import ast,inspect,textwrap

def controlled_support_gate(scene,binding):
    from controlled_multi_future import high_level_physical_runner_v1 as original
    tree=ast.parse(textwrap.dedent(inspect.getsource(original.execute_f2_controlled_insertion_physical_v2)))
    body=tree.body[0].body;start=next(i for i,n in enumerate(body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='support_rows' for t in n.targets))
    stop=next(i for i,n in enumerate(body[start:],start) if isinstance(n,ast.If) and 'support_gate' in ast.unparse(n.test))
    statements=body[start:stop]+[ast.Return(value=ast.Name(id='support_gate',ctx=ast.Load()))]
    fn=ast.FunctionDef(name='gate',args=ast.arguments(posonlyargs=[],args=[ast.arg(arg='scene'),ast.arg(arg='binding'),ast.arg(arg='can_name')],kwonlyargs=[],kw_defaults=[],defaults=[]),body=statements,decorator_list=[])
    ns=dict(vars(original));exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'original_controlled_support_gate_extraction','exec'),ns)
    return ns['gate'](scene,binding,original._entity(scene.can).get_name())

def release_safety_v10(scene,binding,selected_finger_link_names):
    from controlled_multi_future import high_level_physical_runner_v1 as original
    from controlled_multi_future.f2_release_gates_v10 import audit_f2_release_safety_gate_v10
    rows=scene.trace[-50:]
    values=[{'actor_linear_velocity':r['actor_linear_velocity'],'actor_angular_velocity':r['actor_angular_velocity'],
             'contact_pairs':r['contact_pairs'],'contact_signal_complete':original._complete_contact_signal(r)} for r in rows]
    geometry=[original._inside_opening_geometry(scene,binding,can_actor_pose=r['role_actor_poses']['main_can'],box_actor_pose=r['role_actor_poses']['box']) for r in rows]
    return audit_f2_release_safety_gate_v10(values,geometry,can_actor_name=original._entity(scene.can).get_name(),
                                          selected_finger_link_names=selected_finger_link_names,box_actor_name=original._entity(scene.box).get_name())

def final_inside_v10(scene,binding,settle_rows,*,arm_rest_pass):
    from controlled_multi_future import high_level_physical_runner_v1 as original
    from controlled_multi_future.f2_release_gates_v10 import audit_f2_final_inside_success_gate_v10
    predicates=original._f2_relation_predicates(scene,binding)
    rows=[{'actor_linear_velocity':r['actor_linear_velocity'],'actor_angular_velocity':r['actor_angular_velocity'],
           'contact_pairs':r['contact_pairs'],'contact_signal_complete':original._complete_contact_signal(r)} for r in settle_rows]
    return audit_f2_final_inside_success_gate_v10(rows,true_cavity_obb_pass=predicates['inside'],relation_predicates=predicates,gripper_full_open=original._arm_gripper_open(scene,'left'),
      arm_rest_pass=arm_rest_pass,can_actor_name=original._entity(scene.can).get_name(),box_actor_name=original._entity(scene.box).get_name())
