"""Spec-driven F1 actor construction, with lazy native simulator boundary."""
from copy import deepcopy
import numpy as np


def create_roles(scene, spec, *, box, asset, pose):
    """Callbacks here are the actual simulator boundary; tests replace only these."""
    result = {}
    for r in spec['roles']:
        name = r['role']
        if name in result:
            raise ValueError('duplicate physical role')
        if r['asset'] == 'primitive_box':
            size = np.asarray(r['size'], dtype=float)
            if size.shape != (3,) or np.any(size <= 0):
                raise ValueError('invalid box size')
            actor = box(scene, pose(r['pose'][:3], r['pose'][3:]), size / 2, color=r['color'], is_static=not r['dynamic'], name=f'formal_f1_{name}')
            actor._cmf_half_extents = size / 2
            actor._cmf_geometry_source = 'frozen_generic_role_size'
        elif r['asset'] == '062_plasticbox:model3' and name == 'common_box':
            actor = asset(scene, pose(r['pose'][:3], r['pose'][3:]), '062_plasticbox', convex=True, is_static=True, model_id=3)
        else:
            raise ValueError(f'unsupported native F1 asset: {r["asset"]}')
        actor.set_name(f'formal_f1_{name}')
        result[name] = actor
        setattr(scene, 'box' if name == 'common_box' else name, actor)
    if not {'red','green','blue','common_box'}.issubset(result):
        raise ValueError('F1 semantic roles missing')
    scene.role_actors = result
    return result


def bind_cameras(scene, spec):
    import sapien
    c = spec['cameras']
    cameras = scene.cameras
    width, height = c['width'], c['height']
    # Replace owned cameras before t0 with explicit resolution. Wrist pose updates
    # still use native update_picture/_update_render mounting behavior.
    def replace(old, name):
        new = scene.scene.add_camera(name=name, width=width, height=height, fovy=float(old.fovy), near=old.get_near(), far=old.get_far())
        new.set_local_pose(old.get_local_pose())
        scene.scene.remove_camera(old)
        return new
    for name in ('left_camera','right_camera'):
        setattr(cameras, name, replace(getattr(cameras, name), name))
    for i, name in enumerate(cameras.static_camera_name):
        camera = replace(cameras.static_camera_list[i], name)
        cameras.static_camera_list[i] = camera
        if name == 'head_camera':
            k = np.asarray(c['head']['K'])
            camera.set_perspective_parameters(.1,100,float(k[0,0]),float(k[1,1]),float(k[0,2]),float(k[1,2]),float(k[0,1]))
            e = np.eye(4); e[:3] = c['head']['extrinsic_cv']
            cv_from_sapien = np.eye(4); cv_from_sapien[:3,:3] = [[0,-1,0],[0,0,-1],[1,0,0]]
            camera.entity.set_pose(sapien.Pose(np.linalg.inv(e) @ cv_from_sapien))
    actual = cameras.get_config()
    if not set(c['required']).issubset(actual):
        raise ValueError('required native camera missing')
    if not np.allclose(actual['head_camera']['intrinsic_cv'], c['head']['K'], atol=1e-4) or not np.allclose(actual['head_camera']['extrinsic_cv'], c['head']['extrinsic_cv'], atol=1e-5):
        raise ValueError('head camera readback does not match frozen spec')


def context_class(base):
    class GenericF1Context(base):
        def __enter__(self):
            if self._a0_phase:
                raise ValueError('formal context not an A0 diagnostic entry')
            from controlled_multi_future.probes.action_feasibility_v2 import _scene_resources
            from controlled_multi_future.real_sapien_adapter_v1_2 import CANONICAL_SETTLE_STEPS
            from envs.utils import create_box, create_actor
            import sapien
            scenes, scene_args = _scene_resources()
            spec = self.planned_spec
            class Scene(scenes['F1']):
                def load_actors(self):
                    create_roles(self, spec, box=create_box, asset=create_actor, pose=sapien.Pose)
            try:
                scene = Scene(); self._scene = scene
                args = scene_args('F1', self.output_root / self.scene_instance_id)
                args['seed'] = int(spec['seed'])
                scene._cmf_planned_root_slot_spec = deepcopy(spec)
                scene.setup_demo(**args)
                bind_cameras(scene, spec)
                for _ in range(CANONICAL_SETTLE_STEPS): scene.scene.step()
                scene._cmf_setup_kwargs = args
                scene._cmf_canonical_settle_steps = CANONICAL_SETTLE_STEPS
                scene._cmf_scene_instance_id = self.scene_instance_id
                scene._cmf_adapter_version = 'formal_f1_native_entry_20260910'
                scene._cmf_sealed_implementation_source_sha256 = self.sealed_implementation_source_sha256
                scene._cmf_sealed_source_binding = self.sealed_source_binding
                scene._cmf_scene_context_v1_2 = self
                self.handle.scene = scene
                return self.handle
            except BaseException as exc:
                self.__exit__(type(exc), exc, exc.__traceback__)
                raise
    return GenericF1Context
