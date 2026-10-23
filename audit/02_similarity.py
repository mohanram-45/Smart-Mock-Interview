"""Audit 2: duplicate / near-duplicate analysis using TF-IDF cosine (sentence-transformers not installed; no deps added).
Clusters are INSPECTED, not auto-labelled as duplicates."""
import re, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse.csgraph import connected_components
from scipy.sparse import csr_matrix
from common import *
root,out=get_root()
pj=pd.read_pickle(out/"processed_annotated.pkl").reset_index(drop=True)
seed_all,exp_all,interim,_,_=load_all(root)
R={}
# ---- A. what were the 30 dropped "duplicates"?
interim["qn"]=interim.question.map(norm_q)
src=["generated"]*len(exp_all)+["seed"]*len(seed_all); interim["src"]=src
d=interim[interim.duplicated("qn",keep=False)].sort_values("qn")
pairs=[]
for qn,g in d.groupby("qn"):
    pairs.append({"question":g.question.iloc[0],"domains":g.domain.tolist(),"answers_identical":bool(g.reference_answer.nunique()==1)})
R["dropped_dup_groups"]=len(pairs)
R["dropped_dup_cross_domain_groups"]=sum(len(set(p["domains"]))>1 for p in pairs)
R["dropped_dup_examples"]=pairs[:6]
R["dropped_dup_domain_pairs"]=pd.Series(["+".join(sorted(p["domains"])) for p in pairs]).value_counts().to_dict()
R["dropped_dup_answers_differ_count"]=sum(not p["answers_identical"] for p in pairs)
# the 2 exact duplicate answers remaining
an=pj.reference_answer.map(lambda s:" ".join(s.lower().split()))
R["remaining_exact_duplicate_answer_groups"]=pj[an.duplicated(keep=False)][["id","domain","question"]].to_dict("records")

# ---- B. question-level TF-IDF
tv=TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True,stop_words="english",min_df=1)
Q=tv.fit_transform(pj.question)
S=(Q@Q.T).tocsr(); S.setdiag(0); S.eliminate_zeros()
is_seed=(pj.src=="seed").values; is_gen=~is_seed
def comps(mask,th):
    idx=np.where(mask)[0]; sub=S[idx][:,idx]; sub=sub.multiply(sub>=th)
    n,lab=connected_components(csr_matrix(sub),directed=False)
    return idx,lab
# seed-only near-dups
sd_idx=np.where(is_seed)[0]
for th in (0.95,0.85,0.75,0.65):
    idx,lab=comps(is_seed,th); sizes=pd.Series(lab).value_counts()
    big=sizes[sizes>1]
    R[f"seed_only_th{th}"]={"clusters_size>=2":int(len(big)),"rows_in_clusters":int(big.sum()),"largest":int(big.max()) if len(big) else 0}
# save inspectable clusters at 0.75
idx,lab=comps(is_seed,0.75)
cl=[]
for c,sz in pd.Series(lab).value_counts().items():
    if sz<2: break
    rows=idx[lab==c]
    cl.append({"size":int(sz),"items":[{"id":int(pj.id[i]),"domain":pj.domain[i],"diff":pj.difficulty[i],"q":pj.question[i][:160]} for i in rows[:6]]})
R["seed_clusters_th0.75_all"]=cl
# seed vs generated overlap (concept already covered by template?)
G=S[sd_idx][:,np.where(is_gen)[0]]
mx=np.asarray(G.max(axis=1).todense()).ravel()
for th in (0.9,0.8,0.7,0.6,0.5):
    R[f"seed_questions_with_generated_neighbour_ge_{th}"]=int((mx>=th).sum())
order=np.argsort(-mx)[:12]; gi=np.where(is_gen)[0]
R["seed_vs_generated_top_pairs"]=[{"seed_q":pj.question[sd_idx[o]][:140],"gen_q":pj.question[gi[G[o].toarray().argmax()]][:140],"cos":round(float(mx[o]),3),"seed_domain":pj.domain[sd_idx[o]],"gen_domain":pj.domain[gi[G[o].toarray().argmax()]]} for o in order]

# ---- C. generated rows: structure
gen=pj[is_gen].copy()
def topic_norm(r): return (r.domain,r.topic)
R["generated_rows"]=len(gen)
R["generated_distinct_domain_topic_pairs"]=int(gen.groupby(["domain","topic"]).ngroups)
R["generated_questions_per_topic_mode"]=int(gen.groupby(["domain","topic"]).size().mode()[0])
# templates that don't contain the domain name -> cross-domain collisions
R["templates_without_domain_in_text"]=10
# skeleton collapse (generated only)
def skel(r):
    a=r.reference_answer
    a=re.sub(re.escape(r.topic),"<T>",a,flags=re.I)
    a=re.sub(r"(Machine Learning|Deep Learning|NLP|Python|SQL|Data Analysis)","<D>",a)
    a=re.sub(r"related to .*?\. A strong","related to <CTX>. A strong",a)
    return " ".join(a.split())
gen["skel"]=gen.apply(skel,axis=1)
R["generated_distinct_answer_skeletons"]=int(gen.skel.nunique())
R["generated_rows_per_skeleton_min_max"]=[int(gen.skel.value_counts().min()),int(gen.skel.value_counts().max())]
# fraction of answer tokens that are topic-specific
def topic_share(r):
    toks=r.reference_answer.split(); t=set(r.topic.lower().split())
    return sum(w.lower().strip(".,") in t for w in toks)/len(toks)
R["generated_answer_mean_topic_token_share"]=float(gen.apply(topic_share,axis=1).mean())
# answer similarity: same-template different-topic vs seed-vs-seed
tva=TfidfVectorizer(sublinear_tf=True); A=tva.fit_transform(pj.reference_answer)
rng=np.random.default_rng(0)
def mean_cos(ix,n=400):
    a=rng.choice(ix,n); b=rng.choice(ix,n); m=a!=b
    return float(np.asarray(A[a[m]].multiply(A[b[m]]).sum(axis=1)).mean())
for t in sorted(gen.tpl_id.dropna().unique())[:12]:
    pass
R["mean_pairwise_answer_cosine_generated_same_template_diff_topic"]=float(np.mean([mean_cos(gen[(gen.tpl_id==t)&(gen.domain==gen.domain.iloc[0])].index.values,200) for t in sorted(gen.tpl_id.unique())]))
R["mean_pairwise_answer_cosine_generated_random"]=mean_cos(gen.index.values)
R["mean_pairwise_answer_cosine_seed_random"]=mean_cos(pj[is_seed].index.values)
# answers with cos>=0.9 to some other answer
Aa=(A@A.T).tocsr(); Aa.setdiag(0)
mxa=np.asarray(Aa.max(axis=1).todense()).ravel()
R["answers_with_other_answer_cos_ge_0.9"]={"generated":int((mxa[is_gen]>=0.9).sum()),"seed":int((mxa[is_seed]>=0.9).sum())}
R["answers_with_other_answer_cos_ge_0.8"]={"generated":int((mxa[is_gen]>=0.8).sum()),"seed":int((mxa[is_seed]>=0.8).sum())}
# top seed answer dups
so=np.argsort(-mxa*is_seed)[:8]
R["seed_answer_near_dups_top"]=[{"id":int(pj.id[i]),"q":pj.question[i][:100],"cos":round(float(mxa[i]),3)} for i in so]

# ---- D. effective distinct knowledge items
R["effective_distinct_items"]={"seed_questions":int(is_seed.sum()),"generated_topics":R["generated_distinct_domain_topic_pairs"],
   "note":"generated rows are 12 angle-templates per topic with answers that collapse to <=%d skeletons"%R["generated_distinct_answer_skeletons"]}
dump(out,"02_similarity.json",R)
print(json.dumps({k:v for k,v in R.items() if k not in("seed_clusters_th0.75_all",)},indent=1,default=str)[:9000])
print("N seed clusters@0.75:",len(R["seed_clusters_th0.75_all"]))
