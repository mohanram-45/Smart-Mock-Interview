import json,copy,re,sys
rev=[];gen={}
for k in "ABC":
    rev+=json.load(open(f"rev_{k}.json"))
    for g in json.load(open(f"gen_{k}.json")): gen[g['plan_id']]=g
order=[p for k in "ABC" for p in [g['plan_id'] for g in json.load(open(f"gen_{k}.json"))]]
out={};log=[];unapplied=[]
for r in rev:
    g=copy.deepcopy(gen[r['plan_id']]);pid=g['plan_id']
    g['original_difficulty']=g['difficulty']; g['difficulty']=r['difficulty_blind']
    if r.get('suggested_type'): log.append((pid,'question_type',g['question_type'],r['suggested_type'])); g['question_type']=r['suggested_type']
    if r.get('suggested_key_concepts'): log.append((pid,'key_concepts',g['key_concepts'],r['suggested_key_concepts'])); g['key_concepts']=r['suggested_key_concepts']
    if r.get('rubric_points'): g['rubric_points']=r['rubric_points']
    g['added_sources']=r.get('added_sources') or []
    for i in r['issues']:
        f=i['field']; claim=i['claim']; rep=i['replacement']
        if f.startswith('code.'):
            k=f.split('.')[1]; txt=g['code'][k]
        else: txt=g.get(f)
        if txt is None or txt.count(claim)!=1: unapplied.append((pid,f,claim[:60],0 if txt is None else txt.count(claim))); continue
        new=txt.replace(claim,rep)
        if f.startswith('code.'): g['code'][k]=new
        else: g[f]=new
        log.append((pid,f,claim,rep,i['severity']))
    cp=r.get('code_patch')
    if cp:
        for k in('solution','test'):
            if cp.get(k): log.append((pid,'code_patch.'+k,g['code'][k][:80],cp[k][:80])); g['code'][k]=cp[k]
    g['review_verdict']=r['verdict']; g['major_first_review']=any(i['severity']=='major' for i in r['issues'])
    out[pid]=g
json.dump([out[p] for p in order],open("corrected_1.json","w"),indent=1)
json.dump(log,open("corrections_log_1.json","w"),indent=1)
print(len(out),len(log),"unapplied:",unapplied)
