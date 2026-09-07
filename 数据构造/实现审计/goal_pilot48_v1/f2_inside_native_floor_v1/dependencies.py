"""Read-only source/approval binding bundle, no GPU issuer."""
from pathlib import Path
from .certificate import sha,load,VERSION

def bindings():
    root=Path(__file__).parent;r=load(root/'CPU_AUDIT_V1_1.json')
    for table in ('source_files','input_files'):
        for p,h in r[table].items():
            if sha(p)!=h:raise ValueError('native-floor audited source changed: '+p)
    sources=dict(r['source_files']);sources[str(Path(__file__))]=sha(__file__)
    inputs={**r['input_files'],**{str(root/n):sha(root/n) for n in ('CPU_AUDIT_V1_1.json','support_shape_certificate.json','saved_contact_geometry.json')}}
    return {'source_files':sources,'input_files':inputs,'verifier_version':VERSION,
      'certificate_sha256':r['certificate_sha256'],'no_GPU_execution_authority_issued_here':True}
