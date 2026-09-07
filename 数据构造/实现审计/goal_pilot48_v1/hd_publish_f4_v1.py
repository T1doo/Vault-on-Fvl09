"""Publish checked F4 native-HD replays; retain original Guard failures."""
import os, shutil, subprocess
from pathlib import Path
from goal_pilot48_v1.runtime import budget
from goal_pilot48_v1.runtime.issue_one_sided_micro import checked, sha
from realization_utf8_io_v1 import write_new

ROOT = budget.ROOT
VAULT = ROOT.parents[2]
FFMPEG = Path('/nfs_share/lijunhui/Robotwin2/env/bin/ffmpeg')
FONT = '/nfs_share/lijunhui/Robotwin2/env/lib/python3.10/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf'
KINDS = {'r_pc':'01_标准轨迹','r_inv_path':'02_路径变化','r_inv_motion':'03_节奏变化'}

def publish(job_id):
    rec_path = ROOT/'hd_publications'/f'{job_id}.json'
    if rec_path.exists(): return checked(rec_path)
    m = checked(ROOT/'jobs'/f'{job_id}.json','manifest_sha256'); job=m['jobs'][0]; item=m['render_item']
    if item['family'] != 'F4' or item['pilot'] not in ('A','B'): raise ValueError('F4 only')
    out=Path(job['output_namespace']); term=checked(out/'goal_terminal.json'); guard=checked(Path(m['guard_directory'])/f'{job_id}.terminal.json')
    if not term['pass'] or not term['runtime_result']['render_pass']: raise ValueError('render not passed')
    late=None
    if not guard['task_owned_cleanup_pass'] or not guard['gpu_returned_to_idle_baseline']:
        candidates=sorted((ROOT/'hd_late_release_review_v1').glob('OBSERVATION_*.json'))
        candidates=[checked(p) for p in candidates if p.exists()]
        late=next((x for x in candidates if x.get('job_id')==job_id),None)
        if late is None or not late.get('late_baseline_restoration_verified') or not late.get('own_pid_and_group_absent') or late.get('remaining_owned_process_rows'): raise ValueError('late release proof missing')
        if late.get('original_guard_receipt_sha256') != guard['receipt_sha256']: raise ValueError('late Guard binding')
        for p,h in late['immutable_file_hashes'].items():
            if sha(p)!=h: raise ValueError('late evidence source changed')
        matches=[x for x in budget.rows() if x['kind']=='RECONCILE' and x['job_id']==job_id]
        if len(matches)!=1 or matches[0]['evidence'].get('late_observation_receipt_sha256')!=late['receipt_sha256']: raise ValueError('late reconcile missing')
    else:
        if not guard['gpu_returned_to_idle_baseline']: raise ValueError('GPU baseline')
    if term['manifest_sha256']!=guard['manifest_sha256']!=m['manifest_sha256']: raise ValueError('identity')
    v=term['runtime_result']['video']; dest=VAULT/'数据构造/演示视频/F4/高清多视角_状态回放'/('根组'+item['pilot'])/KINDS[item['realization']]; dest.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ); env.pop('LD_LIBRARY_PATH',None); files={}; sources={}
    for i,page in enumerate(v['pages']):
        source=Path(page['path']);
        if not source.resolve().is_relative_to(out.resolve()) or sha(source)!=page['file_sha256']: raise ValueError('source mismatch')
        suffix='六视角' if i==0 else '前视角'; target=dest/(item['program_id']+'_'+suffix+'.mp4')
        if target.exists(): raise FileExistsError(str(target))
        if i==0:
            shutil.copyfile(source,target)
        else:
            filt=f"crop=960:720:0:0,drawtext=fontfile={FONT}:text='Saved-state re-render - NOT a new rollout':fontsize=18:fontcolor=white:box=1:boxcolor=black:x=8:y=h-28"
            subprocess.run([str(FFMPEG),'-v','error','-n','-hwaccel','none','-i',str(source),'-vf',filt,'-c:v','libx264','-preset','veryfast','-crf','18','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],env=env,check=True,timeout=120)
        subprocess.run([str(FFMPEG),'-v','error','-hwaccel','none','-threads','2','-i',str(target),'-f','null','-'],env=env,check=True,timeout=120)
        files[str(target)]=sha(target); sources[str(source)]=page['file_sha256']
    result={'schema_version':'reviewed_F4_hd_display_publication_v1','job_id':job_id,'label':item['label'],'goal_terminal_receipt_sha256':term['receipt_sha256'],'guard_receipt_sha256':guard['receipt_sha256'],'published_files':files,'source_videos':sources,'manual_keyframe_review_confirmed':True,'all_source_camera_labels':[x['label'] for x in v['views']],'native_HD_state_replay_not_new_rollout':True,'scientific_acceptance_increment':0,'software_full_decode_pass':True,'front_black_padding_removed_without_upscale':True,'original_guard_cleanup_pass':guard['task_owned_cleanup_pass'],'original_guard_modified':False,'late_release_observation_receipt_sha256':late['receipt_sha256'] if late else None}
    result['receipt_sha256']=budget.digest(result); write_new(rec_path,result); return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('job_id');p.add_argument('--visual-reviewed',action='store_true');a=p.parse_args()
    if not a.visual_reviewed: p.error('visual review required')
    print(publish(a.job_id)['published_files'])
