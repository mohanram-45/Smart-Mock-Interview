import json
c=json.load(open('corrected_1.json')); log=json.load(open('corrections_log_1.json'))
Q={'B4-MLO-13-4':'Near-duplicate intent of smi-k0015 (batch 2): same 200-case prompt-regression gate scenario, paired comparison and gate sizing; reviewer recommended curator decision; quarantined to keep the dataset free of intent duplicates.'}
json.dump(Q,open('quarantined.json','w'),indent=1)
c=[g for g in c if g['plan_id'] not in Q]
S={}
for g in c:
    cur=[dict(s) for s in g['sources']]
    for a in g['added_sources']:
        hit=[s for s in cur if s['url']==a['url']]
        if hit: hit[0]['supports']=a.get('supports',hit[0]['supports']); hit[0]['quote']=a.get('quote',hit[0].get('quote','')); hit[0]['corrected_by_review']=True
        else: cur.append(dict(title=a.get('title',''),url=a['url'],supports=a.get('supports',''),quote=a.get('quote',''),type=a.get('type','official_doc'),added_by_review=True))
    if g['plan_id']=='B4-MLO-11-5': cur=[s for s in cur if 'security-top-ten' not in s['url']]
    S[g['plan_id']]=cur
json.dump(S,open('sources_merged_1.json','w'),indent=1)
chg={}
for l in log:
    if len(l)==4: l=list(l)+['code_patch']
    chg.setdefault(l[0],[]).append(l)
rc=[g for g in c if g['review_verdict']=='correct']
print(len(c),len(rc),sum(len(S[g['plan_id']]) for g in c))
n=4
for i in range(n):
    part=rc[i::n]
    json.dump(part,open(f'rc_in_{i}.json','w'),indent=1)
    json.dump([x for g in part for x in chg.get(g['plan_id'],[])],open(f'rc_changes_{i}.json','w'),indent=1)
    print(i,[g['plan_id'] for g in part])
ent=[dict(entry_id=f"{p}#{i}",plan_id=p,url=s['url'],title=s['title'],quote=s.get('quote',''),supports=s['supports'],claimed_status='opened_by_author_or_reviewer') for p,v in S.items() for i,s in enumerate(v)]
k=3
for i in range(k): json.dump(ent[i::k],open(f'sv_in_{i}.json','w'),indent=1)
print(len(ent))
json.dump(c,open('corrected_1.json','w'),indent=1)
