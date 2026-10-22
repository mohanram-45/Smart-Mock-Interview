import json,copy
d={g['plan_id']:g for g in json.load(open("corrected_1.json"))}; order=list(d)
S=json.load(open("sources_merged_1.json"))
rc=[]
for n in range(4): rc+=json.load(open(f"rc_out_{n}.json"))
sv={}
for n in range(3):
    for v in json.load(open(f"sv_out_{n}.json")): sv[v['entry_id']]=v
log=[];un=[];hist={}
def fix(g,f,c,rep,origin):
    t=g.get(f)
    if f.startswith('code.'): return
    if not rep or t is None or t.count(c)!=1: un.append((g['plan_id'],f,c[:70],origin)); return
    g[f]=t.replace(c,rep); log.append((g['plan_id'],f,c,rep,origin))
for r in rc:
    g=d[r['plan_id']]; g['recheck_verdict']=r['verdict']; g['major_recheck']=any(i['severity']=='major' for i in r['issues']); g['difficulty_recheck']=r['difficulty_blind']
    if r.get('suggested_type'): log.append((g['plan_id'],'question_type',g['question_type'],r['suggested_type'],'recheck')); g['question_type']=r['suggested_type']
    if r.get('rubric_points') and not g.get('rubric_points'): g['rubric_points']=r['rubric_points']
    if r.get('suggested_key_concepts'): g['key_concepts']=r['suggested_key_concepts']
    for i in r['issues']: fix(g,i['field'],i['claim'],i['replacement'],'recheck_'+i['severity'])
    for s in r.get('added_sources') or []:
        if s['url'] not in [x['url'] for x in S[g['plan_id']]]: S[g['plan_id']].append({"title":s.get('title',''),"url":s['url'],"supports":s.get('supports',''),"quote":s.get('quote',''),"type":s.get('type','official_doc'),"added_by_recheck":True})
for eid,v in sv.items():
    pid=eid.split('#')[0]; i=int(eid.split('#')[1]); g=d[pid]
    for x in v.get('fixes') or []: fix(g,x['field'],x['claim'],x['replacement'],'source_verifier')
    s=S[pid][i]; s['verify']=v['verdict']
    if v['verdict']=='partial' and v.get('narrowed_supports'): s['supports']=v['narrowed_supports']
    if v['verdict'] in('not_supported','unreachable'): s['drop']=True
for pid in S: S[pid]=[s for s in S[pid] if not s.get('drop')]
for g in d.values():
    c=g.get('concise_answer')
    if c and len(c.split())>80: print("concise>80",g['plan_id'],len(c.split()))
json.dump([d[p] for p in order],open("corrected_2.json","w"),indent=1)
json.dump(S,open("sources_merged_2.json","w"),indent=1); json.dump({"applied":log,"skipped":un},open("round2_log.json","w"),indent=1)
print(len(log),"applied; skipped:",un)
print("changed records:",sorted({l[0] for l in log}))
