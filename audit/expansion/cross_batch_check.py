import pandas as pd, json, re, hashlib, itertools
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
R=Path(__file__).resolve().parents[2]
rd=lambda p: pd.read_csv(R/p,keep_default_na=False,dtype=str)
v5=rd('data/curated/v5/curated_questions.csv'); v5['src']='v5'
fr=[v5]; qr=[]
for n in range(1,5):
    b=rd(f'data/expansion/batch_0{n}/batch_0{n}_accepted.csv'); b['src']=f'B{n}'; fr.append(b)
    q=R/f'data/expansion/batch_0{n}/quarantine.csv'
    if q.exists():
        x=pd.read_csv(q,keep_default_na=False,dtype=str); x['src']=f'B{n}'; qr.append(x)
A=pd.concat(fr,ignore_index=True); out={}
out['counts']=A.src.value_counts().to_dict(); out['total']=len(A)
out['id_collisions']=A.id[A.id.duplicated(keep=False)].tolist()
norm=lambda s: re.sub(r'\W+',' ',s.lower()).strip()
out['exact_dup_questions']=A[A.question.map(norm).duplicated(keep=False)].id.tolist()
out['exact_dup_answers']=A[A.answer.map(norm).duplicated(keep=False)].id.tolist()
# metadata
new=A[A.src!='v5']
miss={}
for c in ['id','domain','topic','difficulty','question_type','question','answer','key_concepts','common_mistakes','version','introduced_in','verification']:
    e=A[A[c].str.strip()==''].id.tolist()
    if e: miss[c]=e[:20]+(['...']if len(e)>20 else [])
out['missing_core_metadata']=miss
out['difficulty_values']=A.difficulty.value_counts().to_dict(); out['type_values']=A.question_type.value_counts().to_dict()
out['domain_values']=A.groupby('src').domain.value_counts().unstack(0).fillna(0).astype(int).to_dict()
out['bad_difficulty']=A[~A.difficulty.isin(['Easy','Medium','Hard'])].id.tolist()
# answer consistency in new batches
inc=[]
for _,r in new.iterrows():
    if r.answer_set.strip():
        det=r.detailed_answer.strip(); sing=r.concise_answer.strip()
        if r.answer.strip() not in (det,) and r.answer.strip()!=r.detailed_answer.strip(): inc.append(r.id)
out['answer_ne_detailed']=inc
dom_new=new.groupby('id').domain.first()
out['new_domain_per_batch']={s:g.domain.value_counts().to_dict() for s,g in new.groupby('src')}
out['quarantined']=[(x.src.iloc[0], x.iloc[:, :2].values.tolist()) for x in qr if len(x)]
# semantic
txt=(A.question+' '+A.answer).tolist()
tf=TfidfVectorizer(stop_words='english',ngram_range=(1,2),sublinear_tf=True).fit_transform(txt)
S=cosine_similarity(tf); import numpy as np
pairs=[]
srcs=A.src.values
for i,j in zip(*np.where(np.triu(S,1)>0.30)):
    if srcs[i]!=srcs[j] or srcs[i]!='v5':
        pairs.append((float(S[i,j]),A.id[i],A.id[j],A.question[i][:110],A.question[j][:110]))
pairs.sort(reverse=True); out['n_pairs_gt_0.30_involving_new']=len(pairs)
out['top_pairs']=pairs[:60]
# question-only similarity
tq=TfidfVectorizer(stop_words='english',ngram_range=(1,2),sublinear_tf=True).fit_transform(A.question.tolist()); Q=cosine_similarity(tq)
qp=[(float(Q[i,j]),A.id[i],A.id[j],A.question[i][:110],A.question[j][:110]) for i,j in zip(*np.where(np.triu(Q,1)>0.55)) if srcs[i]!='v5' or srcs[j]!='v5']
qp.sort(reverse=True); out['question_pairs_gt_0.55_involving_new']=len(qp); out['top_question_pairs']=qp[:30]
json.dump(out,open(R/'reports/cross_batch_results.json','w'),indent=1,default=str)
for k in ['counts','total','id_collisions','exact_dup_questions','exact_dup_answers','missing_core_metadata','bad_difficulty','answer_ne_detailed','n_pairs_gt_0.30_involving_new','question_pairs_gt_0.55_involving_new','quarantined']: print(k,out[k])
for p in out['top_question_pairs'][:15]: print(p)
