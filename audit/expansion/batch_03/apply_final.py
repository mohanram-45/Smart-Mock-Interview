import json
d={g['plan_id']:g for g in json.load(open("corrected_2.json"))}; order=list(d)
S=json.load(open("sources_merged_2.json"))
fr=[]
for n in range(3): fr+=json.load(open(f"fr_out_{n}.json"))
log=[];un=[]
for r in fr:
    g=d[r['plan_id']]; g['final_verdict']=r['verdict']; g['major_final']=any(i['severity']=='major' for i in r['issues']); g['difficulty_final']=r['difficulty_blind']
    if r.get('rubric_points') and not g.get('rubric_points'): g['rubric_points']=r['rubric_points']
    for i in r['issues']:
        f,c,rep=i['field'],i['claim'],i.get('replacement'); t=g.get(f)
        if f.startswith('code.') or not rep or t is None or t.count(c)!=1: un.append((g['plan_id'],f,c[:80])); continue
        g[f]=t.replace(c,rep); log.append((g['plan_id'],f,c,rep,'final_'+i['severity']))
    for s in r.get('added_sources') or []:
        if s['url'] not in [x['url'] for x in S[g['plan_id']]]: S[g['plan_id']].append({"title":s.get('title',''),"url":s['url'],"supports":s.get('supports',''),"quote":s.get('quote',''),"type":s.get('type','official_doc'),"added_by_final":True})
    for sf in r.get('sources_findings') or []:
        for s in S[g['plan_id']]:
            if s['url']==sf.get('url') and sf.get('status')=='partial': s['verify']='partial'
    for u in r.get('sources_to_drop') or []: S[g['plan_id']]=[s for s in S[g['plan_id']] if s['url']!=u]
    g['unsourced_final']=r.get('unsourced_claims')
for g in d.values():
    c=g.get('concise_answer')
    if c and len(c.split())>80: print("concise>80",g['plan_id'],len(c.split()))
json.dump([d[p] for p in order],open("corrected_3.json","w"),indent=1)
json.dump(S,open("sources_merged_3.json","w"),indent=1); json.dump({"applied":log,"skipped":un},open("final_log.json","w"),indent=1)
print(len(log),"applied; skipped:",un)
