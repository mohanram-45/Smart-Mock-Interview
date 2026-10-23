import json,copy
c=json.load(open('corrected_post_fv2.json')); d={g['plan_id']:g for g in c}
S=json.load(open('sources_post_fv2.json'))
log=[];un=[]
fvs=[]
for i in range(2): fvs+=json.load(open(f'fv3_out_{i}.json'))
gd=json.load(open('gdpr_out.json'))
def main(g): return 'answer' if g['answer_set']=='single' else 'detailed_answer'
def fix(g,f,c_,rep,origin):
    if f=='canonical_answer': f=main(g)
    if f.startswith('code.'): return
    if f=='rubric_points':
        t=json.dumps(g.get('rubric_points') or [],ensure_ascii=False)
        if rep is not None and t.count(c_)==1:
            g['rubric_points']=json.loads(t.replace(c_,rep)); log.append((g['plan_id'],f,c_,rep,origin)); return
        un.append((g['plan_id'],f,c_[:70],origin)); return
    t=g.get(f)
    if rep is None or t is None or t.count(c_)!=1:
        un.append((g['plan_id'],f,c_[:80],origin)); return
    g[f]=t.replace(c_,rep); log.append((g['plan_id'],f,c_,rep,origin))
for r in fvs:
    g=d[r['plan_id']]; g['fv_verdict']=r['verdict']; g['major_fv']=any(i['severity']=='major' for i in r['issues']); g['difficulty_fv']=r['difficulty_blind']
    cp=r.get('code_patch')
    if cp:
        for k in('solution','test'):
            if cp.get(k): log.append((g['plan_id'],'code_patch.'+k,g['code'][k][:80],cp[k][:80],'fv3_patch')); g['code'][k]=cp[k]; g['_patched']=True
    if r.get('rubric_points') and isinstance(r['rubric_points'],list) and not g.get('rubric_points'): g['rubric_points']=r['rubric_points']; log.append((g['plan_id'],'rubric_points','(none)','added','fv2'))
    if r.get('suggested_type'): log.append((g['plan_id'],'question_type',g['question_type'],r['suggested_type'],'fv')); g['question_type']=r['suggested_type']
    for i in r['issues']: fix(g,i['field'],i['claim'],i.get('replacement'),'fv3_'+i['severity'])
    for a in r.get('added_sources') or []:
        if a['url'] not in [x['url'] for x in S[g['plan_id']]]: S[g['plan_id']].append(dict(title=a.get('title',''),url=a['url'],supports=a.get('supports',''),quote=a.get('quote',''),type=a.get('type','official_doc'),added_by_fv=True))
    for u in r.get('sources_to_drop') or []: S[g['plan_id']]=[s for s in S[g['plan_id']] if s['url']!=u]
    g['unsourced_fv']=r.get('unsourced_claims')
for s in []:
    if s.get('fix') and s['fix'].get('field') not in (None,'unverified_claims_listed'):
        fx=s['fix']; fix(d[s['plan_id']],fx['field'],fx['claim'],fx['replacement'],'gdpr')
json.dump(c,open('corrected_post_fv3.json','w'),indent=1); json.dump(S,open('sources_post_fv3.json','w'),indent=1)
json.dump({'applied':log,'skipped':un},open('fv3_log.json','w'),indent=1)
print(len(log),'applied; skipped:',un)
print(sorted({l[0] for l in log}))
