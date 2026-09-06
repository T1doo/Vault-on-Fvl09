"""Locked-version K0/K1/K2 settings; K labels are NOT compression tokens."""
import copy,hashlib
from pathlib import Path
import yaml
P=Path('/nfs_share/lijunhui/Robotwin2/project/RoboTwin')
T=P/'envs/curobo/src/curobo/content/configs/task'

def profile_config(profile):
    if profile not in ('K0','K1','K2'):raise ValueError('constraint profile')
    files={'base_cfg_file':T/'base_cfg.yml','particle_file':T/'particle_ik.yml','gradient_file':T/'gradient_ik_autotune.yml'}
    configs={k:yaml.safe_load(p.read_text(encoding='utf-8')) for k,p in files.items()}
    disabled=['primitive_collision_cfg'] if profile in ('K0','K1') else []
    if profile=='K0':disabled.append('self_collision_cfg')
    modified=[]
    for file_key,cfg in configs.items():
        for section in ('cost','constraint','convergence'):
            for key in disabled:
                if key in cfg.get(section,{}):
                    cfg[section][key]['weight']=0.0;modified.append(file_key+'.'+section+'.'+key)
    return {'profile':profile,'configs':configs,'disabled_terms':modified,
        'kwargs':{'num_seeds':32,'position_threshold':.005,'rotation_threshold':.05,'grad_iters':100,'seed':1531,
            'use_cuda_graph':False,'self_collision_check':profile!='K0','self_collision_opt':profile!='K0','use_particle_opt':True},
        'source_hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files.values()}}

def validate_profiles():
    profiles=[profile_config(k) for k in ('K0','K1','K2')]
    for p in profiles:
        for cfg in p['configs'].values():
            for section in ('cost','constraint','convergence'):
                if p['profile']=='K0' and 'self_collision_cfg' in cfg.get(section,{}):assert cfg[section]['self_collision_cfg']['weight']==0
                if p['profile']!='K2' and 'primitive_collision_cfg' in cfg.get(section,{}):assert cfg[section]['primitive_collision_cfg']['weight']==0
    assert profiles[0]['kwargs']['self_collision_check'] is False and profiles[0]['kwargs']['self_collision_opt'] is False
    assert profiles[2]['configs']['base_cfg_file']['constraint']['self_collision_cfg']['weight']>0
    assert profiles[2]['configs']['base_cfg_file']['constraint']['primitive_collision_cfg']['weight']>0
    return True
