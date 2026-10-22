import json,re,sys
import numpy as np
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
g=[]
for f in ["gen_A.json","gen_B.json","gen_C.json"]: g+=json.load(open(f))
ex=json.load(open("existing_questions.json"))
print(len(g),Counter(r["status"] for r in g),Counter(r["cell_id"] for r in g))
w=lambda s:len((s or "").split())
bad=[]
for r in g:
    a=r["answer_set"]; need={"single":["answer"],"concise+detailed":["concise_answer","detailed_answer"],"detailed+practical":["detailed_answer","practical_answer"],"concise+detailed+practical":["concise_answer","detailed_answer","practical_answer"]}[a]
    allf=["answer","concise_answer","detailed_answer","practical_answer"]
    for f in allf:
        if (f in need)!=bool(r.get(f)): bad.append((r["plan_id"],"field-mismatch",f))
    if r.get("concise_answer") and w(r["concise_answer"])>80: bad.append((r["plan_id"],"concise>80",w(r["concise_answer"])))
    if r.get("detailed_answer") and not 120<=w(r["detailed_answer"])<=450: bad.append((r["plan_id"],"detailed words",w(r["detailed_answer"])))
    if r.get("answer") and not 60<=w(r["answer"])<=400: bad.append((r["plan_id"],"answer words",w(r["answer"])))
    if not 3<=len(r["key_concepts"])<=8: bad.append((r["plan_id"],"kc",len(r["key_concepts"])))
    fence=sum((r.get(f) or "").count("```python")//1 for f in allf)
    if r.get("code") and fence!=1: bad.append((r["plan_id"],"fences",fence))
    if not r.get("code") and fence: bad.append((r["plan_id"],"fence without code"))
print("mech problems:",bad)
print("difficulty",Counter(r["difficulty"] for r in g),"type",Counter(r["question_type"] for r in g),"answer_set",Counter(r["answer_set"] for r in g))
print("definitional openers",sum(bool(re.match(r"(what is|what are|explain|define|describe)",r["question"].strip(),re.I)) for r in g))
qs=[r["question"] for r in g]; eq=[e["question"] for e in ex]
V=TfidfVectorizer(stop_words="english",ngram_range=(1,2),sublinear_tf=True).fit(qs+eq)
S=cosine_similarity(V.transform(qs),V.transform(eq)); print("max sim to existing",S.max().round(2),[ (g[i]["plan_id"],ex[j]["id"],round(S[i,j],2)) for i,j in zip(*np.where(S>=0.45))])
T=cosine_similarity(V.transform(qs)); np.fill_diagonal(T,0); print("within-batch max",T.max().round(2),[(g[i]["plan_id"],g[j]["plan_id"],round(T[i,j],2)) for i,j in zip(*np.where(np.triu(T)>=0.45))])
print(Counter(" ".join(re.findall(r"[a-z']+",q.lower())[:3]) for q in qs).most_common(5))
print(Counter(len(r["sources"]) for r in g))
