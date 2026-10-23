import json,copy
d={g['plan_id']:g for g in json.load(open("corrected_1.json"))}
order=list(d)
rc=[]
for n in range(3): rc+=json.load(open(f"rc_out_{n}.json"))
log=[];un=[];hist={}
for r in rc:
    g=d[r['plan_id']]; hist[g['plan_id']]=r['verdict']
    if r.get('suggested_type'): log.append((g['plan_id'],'question_type',g['question_type'],r['suggested_type'])); g['question_type']=r['suggested_type']
    if r.get('suggested_key_concepts'): g['key_concepts']=r['suggested_key_concepts']; log.append((g['plan_id'],'key_concepts','',r['suggested_key_concepts']))
    if r.get('rubric_points') and not g.get('rubric_points'): g['rubric_points']=r['rubric_points']
    g['difficulty_recheck']=r['difficulty_blind']
    g['added_sources']=g.get('added_sources',[])+[s for s in (r.get('added_sources') or []) if s not in g.get('added_sources',[])]
    for i in r['issues']:
        f=i['field']; claim=i['claim']; rep=i['replacement']
        if f.startswith('code.'): k=f.split('.')[1]; txt=g['code'][k]
        else: txt=g.get(f)
        if rep is None or txt is None or txt.count(claim)!=1: un.append((g['plan_id'],f,claim[:70],i['severity'])); continue
        if f.startswith('code.'): g['code'][k]=txt.replace(claim,rep)
        else: g[f]=txt.replace(claim,rep)
        log.append((g['plan_id'],f,claim,rep,i['severity']))
    cp=r.get('code_patch')
    if cp:
        for k in('solution','test'):
            if cp.get(k): g['code'][k]=cp[k]; log.append((g['plan_id'],'code_patch.'+k,'',cp[k][:80]))
    g['recheck_verdict']=r['verdict']; g['major_recheck']=any(i['severity']=='major' for i in r['issues'])
json.dump([d[p] for p in order],open("corrected_2.json","w"),indent=1)
json.dump(log,open("corrections_log_2.json","w"),indent=1)
print(len(log),"unapplied",un)
