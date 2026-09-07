"""Publish only completed, manually reviewed F1/F4 HD display videos."""
import argparse,os,shutil,subprocess
from pathlib import Path
from goal_pilot48_v1.runtime import budget
from goal_pilot48_v1.runtime.issue_one_sided_micro import checked,sha
from realization_utf8_io_v1 import write_new
ROOT=budget.ROOT;VAULT=ROOT.parents[2]
FFMPEG=Path('/nfs_share/lijunhui/Robotwin2/env/bin/ffmpeg')
FONT='/nfs_share/lijunhui/Robotwin2/env/lib/python3.10/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf'

def publish(job_id):
    record_path=ROOT/'hd_publications'/f'{job_id}.json'
    if record_path.exists():
        existing=checked(record_path)
        if not all(sha(p)==h for p,h in existing['published_files'].items()):raise ValueError('published video changed')
        return existing
    m=checked(ROOT/'jobs'/f'{job_id}.json','manifest_sha256');job=m['jobs'][0];item=m['render_item']
    if job['kind']!='HD_SAVED_STATE_RENDER' or item['family'] not in ('F1','F4') or item['pilot'] not in ('A','B'):
        raise ValueError('accepted F1/F4 display scope only')
    if Path(item['program_id']).name!=item['program_id']:raise ValueError('unsafe filename')
    out=Path(job['output_namespace']);terminal=checked(out/'goal_terminal.json')
    guard=checked(Path(m['guard_directory'])/f'{job_id}.terminal.json')
    if not terminal['pass'] or not terminal['runtime_result']['render_pass'] or not guard['task_owned_cleanup_pass'] or not guard['gpu_returned_to_idle_baseline']:
        raise ValueError('render or release not verified')
    if terminal['manifest_sha256']!=m['manifest_sha256'] or guard['manifest_sha256']!=m['manifest_sha256']:raise ValueError('identity mismatch')
    kinds={'r_pc':'01_标准轨迹','r_inv_path':'02_路径变化','r_inv_motion':'03_节奏变化'}
    dest=VAULT/'数据构造/演示视频'/item['family']/'高清多视角_状态回放'/('根组'+item['pilot'])/kinds[item['realization']]
    env=dict(os.environ);env.pop('LD_LIBRARY_PATH',None)
    files={};sources={};video=terminal['runtime_result']['video']
    for i,page in enumerate(video['pages']):
        source=Path(page['path'])
        if not source.resolve().is_relative_to(out.resolve()) or sha(source)!=page['file_sha256']:raise ValueError('video source mismatch')
        suffix='六视角' if i==0 and len(page['labels'])==6 else '前视角' if len(page['labels'])==1 and 'front' in page['labels'][0] else f'附加视角{i+1}'
        target=dest/(item['program_id']+'_'+suffix+'.mp4');dest.mkdir(parents=True,exist_ok=True)
        if target.exists():raise FileExistsError('unregistered destination already exists')
        if len(page['labels'])==1:
            filt=f"crop=960:720:0:0,drawtext=fontfile={FONT}:text='Saved-state re-render - NOT a new rollout':fontsize=18:fontcolor=white:box=1:boxcolor=black:x=8:y=h-28"
            subprocess.run([str(FFMPEG),'-v','error','-n','-hwaccel','none','-i',str(source),'-vf',filt,'-c:v','libx264','-preset','veryfast','-crf','18','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],env=env,check=True,timeout=120)
        else:
            with source.open('rb') as src,target.open('xb') as dst:shutil.copyfileobj(src,dst)
            if sha(target)!=page['file_sha256']:raise ValueError('copy mismatch')
        subprocess.run([str(FFMPEG),'-v','error','-hwaccel','none','-threads','2','-i',str(target),'-f','null','-'],env=env,check=True,timeout=120)
        files[str(target)]=sha(target);sources[str(source)]=page['file_sha256']
    result={'schema_version':'reviewed_hd_display_publication_v1','job_id':job_id,'label':item['label'],
            'goal_terminal_receipt_sha256':terminal['receipt_sha256'],'guard_receipt_sha256':guard['receipt_sha256'],
            'published_files':files,'source_videos':sources,'manual_keyframe_review_confirmed':True,
            'all_source_camera_labels':[v['label'] for v in video['views']],
            'native_HD_state_replay_not_new_rollout':True,'scientific_acceptance_increment':0,
            'software_full_decode_pass':True,'front_black_padding_removed_without_upscale':True}
    result['receipt_sha256']=budget.digest(result);record_path.parent.mkdir(exist_ok=True);write_new(record_path,result)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('job_id');parser.add_argument('--visual-reviewed',action='store_true');args=parser.parse_args()
    if not args.visual_reviewed:parser.error('main-agent actual keyframe review required before publication')
    print(publish(args.job_id)['published_files'])
