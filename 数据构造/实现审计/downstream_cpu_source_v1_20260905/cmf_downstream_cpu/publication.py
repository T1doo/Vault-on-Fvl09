"""Real provisional -> final branches -> root -> index publication pipeline."""
import copy
from pathlib import Path
from .io import canonical,sha,seal,load,write_new,publish_identical_or_new
from controlled_multi_future.root_orchestrator_v1_1 import finalize_three_branch_root_v1_1

class TwoPhasePublisher:
    def __init__(self,output,*,writer=write_new):self.output=Path(output);self.writer=writer
    def location(self,root_id):return self.output/'roots'/canonical(root_id)
    def index(self,root_id):return self.output/'acceptance_index'/(canonical(root_id)+'.json')
    def publish(self,root_id,branches,*,reference_current_sha256,cleanup_pass):
        directory=self.location(root_id);index=self.index(root_id)
        if index.exists():
            verified=self.audit(root_id)
            root=load(directory/'root.json')
            if root['provisional_input_sha256']!=canonical(branches):raise ValueError('root identity reused for different inputs')
            return {**verified,'new_registration':False}
        provisional=[]
        for b in branches:
            path=directory/'provisional'/(canonical(b['program_id'])+'.json')
            value=seal({'schema_version':'cmf_provisional_branch_v2','root_id':root_id,'payload':b})
            publish_identical_or_new(path,value,self.writer)
            provisional.append((path,load(path)['payload']))
        actual=[copy.deepcopy(b) for _,b in provisional]
        finalization=finalize_three_branch_root_v1_1(actual,reference_current_sha256=reference_current_sha256,root_cleanup_pass=cleanup_pass)
        if finalization.get('accepted') is not True or not all(b.get('verifier',{}).get('pass') is True for b in actual):raise ValueError('incomplete or invalid root')
        references=[]
        for (old,_),b in zip(provisional,actual):
            p=directory/'finalized'/(canonical(b['program_id'])+'.json')
            record=seal({'schema_version':'cmf_finalized_branch_v2','root_id':root_id,'provisional_file':str(old),
                'provisional_file_sha256':sha(old),'payload':b,'payload_sha256':canonical(b)})
            publish_identical_or_new(p,record,self.writer)
            references.append({'path':str(p),'file_sha256':sha(p),'program_id':b['program_id']})
        root=seal({'schema_version':'cmf_two_phase_root_v2','root_id':root_id,'provisional_input_sha256':canonical(branches),
            'reference_current_sha256':reference_current_sha256,'cleanup_pass':cleanup_pass,'branches':actual,
            'branch_files':references,'finalization':finalization,'status':'publication_ready'})
        publish_identical_or_new(directory/'root.json',root,self.writer)
        self.audit(root_id,require_index=False)
        # Stage/collection acceptance is independent and cannot be inferred here.
        entry=seal({'schema_version':'cmf_publication_index_v2','root_id':root_id,'root_file':str(directory/'root.json'),
            'root_file_sha256':sha(directory/'root.json'),'publication_complete':True,'stage_authorization_granted':False})
        publish_identical_or_new(index,entry,self.writer)
        return {**self.audit(root_id),'new_registration':True}
    def audit(self,root_id,*,require_index=True):
        directory=self.location(root_id);root=load(directory/'root.json')
        if root['root_id']!=root_id:raise ValueError('root identity')
        if require_index:
            entry=load(self.index(root_id))
            if entry['root_id']!=root_id or entry['root_file_sha256']!=sha(directory/'root.json'):raise ValueError('index mismatch')
        observed=[]
        for binding,b in zip(root['branch_files'],root['branches']):
            if sha(binding['path'])!=binding['file_sha256']:raise ValueError('finalized branch file changed')
            record=load(binding['path'])
            if record['payload']!=b or record['payload_sha256']!=canonical(b):raise ValueError('root/disk branch mismatch')
            if sha(record['provisional_file'])!=record['provisional_file_sha256']:raise ValueError('provisional changed')
            observed.append(copy.deepcopy(record['payload']))
        if len(observed)!=3 or len(root['branch_files'])!=3:raise ValueError('incomplete disk publication')
        f=finalize_three_branch_root_v1_1(observed,reference_current_sha256=root['reference_current_sha256'],root_cleanup_pass=root['cleanup_pass'])
        if f!=root['finalization'] or f.get('accepted') is not True:raise ValueError('finalization differs')
        return {'publication_complete':True,'root_id':root_id,'computed_divergence':f['computed_first_post_prefix_divergence_step'],
                'stage_authorization_granted':False}
