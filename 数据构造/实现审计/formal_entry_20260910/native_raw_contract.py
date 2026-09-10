"""Raw numeric/integrity validation without the historical Stage0-only label gate."""
def validate_native_raw_contract(path):
    from controlled_multi_future.raw_writer import validate_raw_artifact_contract
    original=validate_raw_artifact_contract(path)
    if original.get('contract_error') or not original.get('integrity',{}).get('pass') or not original.get('checks'):
        return {**original,'pass':False}
    checks={k:v for k,v in original['checks'].items() if k!='stage0_not_formal'}
    manifest=original['manifest']
    # Native inherited writer outputs the source nonformal labels. This validator
    # never relabels raw and never grants research eligibility from those labels.
    checks['labels_consistent']=type(manifest.get('stage0_data')) is bool and type(manifest.get('stage0_authorized')) is bool and manifest['stage0_data'] == manifest['stage0_authorized'] and manifest.get('formal_data') is False
    return {'pass':all(checks.values()),'checks':checks,'manifest':manifest,'integrity':original['integrity'],'historical_stage0_label_gate_not_applicable':True,'research_eligibility_granted':False}
