"""Audit 5: suspected domain misclassification (keyword heuristic -> candidates only) + benchmark/reference overlap."""
import re, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from common import *
root,out=get_root()
pj=pd.read_pickle(out/"processed_annotated.pkl").reset_index(drop=True)
seed=pj[pj.src=="seed"].copy()
R={}
RULES=[  # (current domain, regex on question, suggested domain)
 ("Machine Learning",r"central limit|confidence interval|hypothesis|significance level|a/b test|chi-square|normal distribution|68 per cent|random variable|degree of freedom|type i and type ii|p-value|gaussian/normal|statistical|significance of an insight|metrics? of success|metric is violating|growth for total|churn","Data Analysis"),
 ("Machine Learning",r"pandas profiling|time series\??$","Data Analysis/Python"),
 ("Machine Learning",r"what is deep learning|neural network|exploding gradient|stochastic gradient descent and gradient descent|fourier|knowledge distillation","Deep Learning"),
 ("Deep Learning",r"bagging and boosting|supervised learning algorithms in deep|unsupervised learning algorithms in deep|prerequisites for starting","Machine Learning/other"),
 ("NLP",r"regular expressions|regular grammar|precision and recall\??$|naive bayes algorithm|what is nltk\??$","Python/ML"),
 ("Python",r"web development|jwt|rest api|flask","out-of-scope (web dev)"),
 ("Python",r"dijkstra|binary search tree|quicksort|bubble sort|singleton","DSA (coding) – keep but label topic"),
]
rows=[]
for cur,rx,sug in RULES:
    m=seed[(seed.domain==cur)&seed.question.str.contains(rx,case=False,regex=True)]
    for _,r in m.iterrows(): rows.append({"id":int(r.id),"current":cur,"suggested":sug,"q":r.question[:90]})
R["suspected_domain_mismatch_candidates_n"]=len(rows)
R["suspected_domain_mismatch_by_rule"]=pd.DataFrame(rows).groupby(["current","suggested"]).size().reset_index().to_dict("records")
R["suspected_domain_mismatch_examples"]=rows[:60]
R["seed_questions_sharing_same_domain_label_but_other_source_domain"]=int(((seed.raw_domain=="PREDICTIVE_MODELLING")).sum())
R["note"]="Candidates only: keyword rules + my reading of question text. Not an accuracy rate. Adjudicated by reading in manual review log."
# benchmark overlap
txt=open(root/"Temp/evaluate_models.py",encoding="utf-8").read()
cases=re.findall(r'"question":\s*(?:\'([^\']+)\'|"([^"]+)")\s*,\s*"reference":\s*((?:"[^"]*"\s*)+)',txt)
tv=TfidfVectorizer(stop_words="english").fit(pj.reference_answer)
ov=[]
for a,b,ref in cases:
    q=a or b; ref=" ".join(re.findall(r'"([^"]*)"',ref))
    m=pj[pj.question.map(norm_q)==norm_q(q)]
    if len(m):
        cos=float((tv.transform([ref])@tv.transform([m.iloc[0].reference_answer]).T).toarray()[0,0])
        ov.append({"q":q,"dataset_id":int(m.iloc[0].id),"cos_curated_reference_vs_dataset_reference":round(cos,3),"dataset_answer_words":int(m.iloc[0].aw)})
    else: ov.append({"q":q,"dataset_id":None})
R["benchmark_cases_overlap"]=ov
dump(out,"05_domain_and_benchmark.json",R)
print(json.dumps(R,indent=1,default=str)[:6500])
