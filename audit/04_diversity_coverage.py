"""Audit 4: residue/bleed, question-type diversity, concept coverage (keyword heuristic), exposure, benchmark overlap."""
import re, ast, warnings; warnings.filterwarnings("ignore")
import pandas as pd
from common import *
root,out=get_root()
pj=pd.read_pickle(out/"processed_annotated.pkl").reset_index(drop=True)
seed=pj[pj.src=="seed"].copy(); gen=pj[pj.src=="generated"].copy()
R={}
# ---------- A. extraction residue & answer bleed (seed answers)
RES={"embedded_next_question":r"(?:^|\s)\d{1,3}[.)]\s+(?:Explain|What|How|Describe|Why|Is|Can|When|Which|List|State|Define|Suppose|Are|Do|Does)\b[^.?]{8,}[.?]",
     "Solution_prefix":r"^\s*Solution\s*:|\bSolution\s*:","Ans_prefix":r"^\s*Ans[.:]\s","missing_table_or_figure":r"(below|following) (table|figure|image|diagram)|as shown (below|above)|see (the )?(figure|table)",
     "ends_with_colon":r":\s*$","leading_dash_bullet":r"^\s*-\s","bullet_glyph":r"[●•▪]","editorial_to_candidate":r"Make sure to answer|This question is (quite )?common|Let us look at|let us take a look|we will look at"}
R["seed_residue"]={}
for k,rx in RES.items():
    m=seed[seed.reference_answer.str.contains(rx,regex=True)]
    R["seed_residue"][k]={"n":len(m),"ids":m.id.astype(int).tolist()[:30]}
anyres=seed.reference_answer.str.contains("|".join(f"(?:{RES[k]})" for k in ["embedded_next_question","Solution_prefix","Ans_prefix","missing_table_or_figure","ends_with_colon","editorial_to_candidate"]),regex=True)
R["seed_rows_with_any_serious_residue"]=int(anyres.sum())
R["seed_rows_with_any_serious_residue_ids"]=seed[anyres].id.astype(int).tolist()
dl=seed[seed.reference_answer.str.contains(RES["embedded_next_question"],regex=True)]
R["answer_bleed_examples"]=[{"id":int(r.id),"q":r.question[:80],"snippet":re.search(RES["embedded_next_question"],r.reference_answer).group(0)[:120]} for _,r in dl.head(8).iterrows()]

# ---------- B. question types (heuristic regex on question text; seed only unless noted)
TYPES=[("coding","\\b(implement|write (a|an|the|code|python|sql|a query)|code (for|to)|from scratch|using (python|nltk|spacy|numpy|pandas|flask|matplotlib|pytest)|program(ming)? (an|a)|create a (simple|basic)|how (to|do you) (tokenize|check word|write|create|use mocking))\\b"),
 ("debugging","\\b(debug|suspicious|what could be wrong|what could be the issue|didn.t run|goes? wrong|issue|error message|why (is|does) .* (fail|not work)|violating your expectations)\\b"),
 ("design_architecture","\\b(design|architecture|end-to-end|build a|construct a|production constraints|how would you (build|implement|design|construct)|system)\\b"),
 ("business_case","\\b(metrics? of success|kpi|revenue|company|product|churn|growth|customers?|users?|uber|netflix|facebook|twitter|spotify|linkedin|groupon|store|franchise)\\b"),
 ("scenario_applied","(^|\\b)(given|suppose|let.s say|say (you|that)|you (have|are|run|want)|imagine|a (data ?set|project|fraud|certain|classifier))\\b|how would you (apply|evaluate|handle|deal|approach|predict|determine|quantify|aggregate)"),
 ("comparison","\\b(difference|differentiate|compare|versus|\\bvs\\b|better than|which is (better|more)|how is .* different|contrast)\\b"),
 ("definition_concept","^(what (is|are|do you (mean|understand)|does)|what.s|define|explain( the)?( term| concept)?|list|name|state|describe|which (ml |machine learning )?(algorithm|technique|ensemble|kind)|why (is|are|do|does)|how (does|do|is|are|many|can|will))")]
def qtype(q):
    ql=q.lower()
    for name,rx in TYPES:
        if re.search(rx,ql): return name
    return "other_unclassified"
seed["qtype"]=seed.question.map(qtype)
R["seed_question_types_by_domain"]=pd.crosstab(seed.domain,seed.qtype).to_dict("index")
R["seed_question_types_overall"]=seed.qtype.value_counts().to_dict()
# generated: by template (assigned by reading the 12 templates)
TPL={0:"definition_concept",1:"definition_concept(why-it-matters)",2:"conceptual(pitfalls)",3:"generic_application",4:"generic_evaluation",5:"comparison(unspecified alternative)",6:"generic_debugging",7:"meta-interview(not a technical question)",8:"conceptual(when-to-avoid)",9:"generic_design",10:"conceptual(failure modes)",11:"generic_trade-offs"}
g=gen.copy(); R["generated_template_type_counts"]={TPL[int(k)]:int(v) for k,v in g.tpl_id.value_counts().items()}
R["generated_with_executable_code_or_sql_task"]=0
R["generated_questions_naming_a_dataset_schema_or_code_snippet"]=int(g.question.str.contains(r"\b(table|dataframe|schema|following (code|query|data))\b",case=False,regex=True).sum())
R["generated_template_7_meta_rows"]=int((g.tpl_id==7).sum())
R["generated_template_5_unspecified_alternative_rows"]=int((g.tpl_id==5).sum())
# ---------- C. concept coverage (keyword on QUESTION text). seed = substantive; generated = topic names only
def cov(domain,concepts):
    s=seed[seed.domain==domain].question.str.lower(); gtopics=set(gen[gen.domain==domain].topic.str.lower())
    rows={}
    for name,rx in concepts.items():
        sn=int(s.str.contains(rx,regex=True).sum()); gn=sum(bool(re.search(rx,t)) for t in gtopics)
        rows[name]={"seed_questions":sn,"generated_topics(12 templated Qs each)":gn}
    return rows
C={}
C["Machine Learning"]=cov("Machine Learning",{
 "linear/logistic regression":r"linear regression|logistic","trees/forests":r"decision tree|random forest","boosting/XGBoost":r"boost|xgboost|gbm","SVM":r"svm|support vector","KNN/k-means/clustering":r"knn|nearest|k-means|clustering",
 "naive bayes":r"naive bayes|naïve","PCA/dim-reduction":r"pca|dimension","preprocessing: scaling/encoding":r"scal|normali[sz]|standardi|encod","missing values/imputation":r"missing|imput","outliers":r"outlier",
 "class imbalance":r"imbalanc","feature engineering/selection":r"feature (eng|select)|feature selection|variable selection","bias-variance/over-underfit":r"bias|variance|overfit|underfit","regularization L1/L2":r"regulari[sz]|lasso|ridge|l1|l2",
 "cross-validation":r"cross.?valid","metrics: ROC/AUC/PR/F1/confusion":r"roc|auc|precision|recall|f1|confusion","hyperparameter tuning":r"hyperparam|grid search|random search","data leakage":r"leak","explainability SHAP/LIME":r"shap|lime|interpret|explainab",
 "model calibration":r"calibrat","drift/monitoring/deployment":r"drift|monitor|deploy|production","pipelines/MLOps":r"pipeline|mlops","time-series":r"time.?series","recommender systems":r"recommend|collaborative|cold start","statistics (CLT/CI/p-value/hypothesis)":r"central limit|confidence interval|p-?value|hypothesis|significance","probability/Bayes":r"bayes|probability|likelihood","A/B testing":r"a/b"})
C["Deep Learning"]=cov("Deep Learning",{
 "backpropagation":r"backprop","activation functions":r"activation|relu|sigmoid|tanh|softmax","CNN":r"cnn|convolution","RNN/LSTM/GRU":r"rnn|lstm|gru|recurrent","transformers/attention":r"transformer|attention","optimizers (Adam/SGD/momentum)":r"adam|sgd|momentum|rmsprop|gradient descent|optimi[sz]er",
 "PyTorch":r"pytorch|torch","TensorFlow/Keras":r"tensorflow|keras","transfer learning/fine-tuning":r"transfer|fine.?tun","batch/layer norm":r"batch ?norm|layer ?norm|normali[sz]ation","dropout/regularization":r"dropout|regulari[sz]","weight init":r"initiali[sz]","vanishing/exploding gradients":r"vanishing|exploding","learning-rate schedules":r"learning rate",
 "loss functions":r"loss|cost function","autoencoders/GAN/VAE":r"autoencoder|gan\b|generative adversarial|vae","embeddings":r"embedding","training loop/inference/serving":r"inference|latency|serving|training loop","GPU/mixed precision":r"gpu|mixed precision","compression/quantization/distillation":r"quanti[sz]|distill|compress|pruning","data augmentation":r"augment","overfitting/early stopping":r"overfit|early stopping","residual connections":r"residual|resnet","tensors":r"tensor"})
C["NLP"]=cov("NLP",{
 "tokenization":r"tokeni[sz]","stemming/lemmatization":r"stemm|lemmat","stop words":r"stop.?word","BoW/TF-IDF/n-grams":r"bag of words|bag-of-words|tf-?idf|n-?gram|unigram","word embeddings (Word2Vec/GloVe)":r"word2vec|glove|word embedding","contextual embeddings/BERT":r"bert|contextual|masked language","transformers":r"transformer","sentence embeddings/semantic search":r"sentence|semantic search|semantic similarity|cosine",
 "information retrieval/BM25":r"retriev|bm25|\bir\b","RAG":r"\brag\b|retrieval.augmented","vector DB/FAISS/ANN":r"vector (db|database|store)|faiss|ann\b|nearest neighbo","chunking":r"chunk","LLM fundamentals":r"\bllm|large language|gpt|prompt|hallucinat","fine-tuning/LoRA/PEFT":r"fine.?tun|lora|peft","NER":r"\bner\b|named entity|entity recognition","POS tagging":r"pos tag|part.?of.?speech|parts-of-speech","sentiment/text classification":r"sentiment|text classif","parsing/syntax/semantics":r"pars|syntactic|semantic analysis|pragmatic","evaluation BLEU/ROUGE/perplexity":r"bleu|rouge|perplexity","retrieval evaluation (recall@k, MRR, nDCG)":r"recall@|mrr|ndcg","text summarization/QA":r"summari[sz]|question answering","topic modelling":r"topic model|lda|latent","language modelling":r"language model"})
C["Python"]=cov("Python",{
 "decorators":r"decorator","generators/iterators":r"generator|iterator|yield","comprehensions":r"comprehension","mutability/tuples/lists/dicts/sets":r"mutab|tuple|list|dict|set\b","copy vs deepcopy":r"deepcopy|shallow","*args/**kwargs":r"args|kwargs","OOP/inheritance":r"class|inherit|object|oop","dunder/magic":r"dunder|__","exceptions":r"exception|try","context managers":r"context manager|with statement","closures/scope/LEGB":r"closure|scope|legb","GIL/threading/multiprocessing":r"gil\b|thread|multiproc","async":r"async|await","NumPy":r"numpy|array|broadcast","Pandas":r"pandas|dataframe","debugging/profiling":r"debug|profil","testing/pytest":r"pytest|unittest|test","type hints/dataclasses":r"type hint|dataclass","algorithms/DSA coding":r"sort|search|tree|stack|queue|graph|dijkstra|fizzbuzz|reverse","regex/file I/O/JSON":r"regex|regular expression|json|csv|file","performance/memory":r"performance|memory|vectori","virtualenv/packaging":r"virtual env|venv|pip|package"})
C["SQL"]=cov("SQL",{
 "joins (inner/left/full/self/cross)":r"join","group by/having/aggregates":r"group by|having|aggregate","subqueries/correlated":r"subquer|correlated","CTEs":r"cte|common table","window functions":r"window","ranking (row_number/rank/dense_rank)":r"row_number|rank","lag/lead/running totals/moving avg":r"lag|lead|running|moving","CASE/NULL/COALESCE":r"case|null|coalesce","indexes/execution plans":r"index|execution plan|query plan","optimisation":r"optimi|slow query","normalisation/keys":r"normali|primary key|foreign key","transactions/ACID/locking":r"acid|transaction|deadlock|isolation","UNION/set ops":r"union|intersect|except","dedup/top-N per group":r"duplicate|top n|top-n|nth","date functions":r"date","cohort/retention/funnel":r"cohort|retention|funnel","views/stored procs":r"view|stored procedure","star schema/warehouse":r"star schema|fact|dimension|warehouse|olap","pivot":r"pivot","write-a-query exercises":r"write a (sql )?query|write sql|query to"})
C["Data Analysis"]=cov("Data Analysis",{
 "EDA":r"\beda\b|exploratory|explor","descriptive statistics":r"mean|median|mode|variance|standard deviation","distributions":r"distribution|normal|poisson|binomial","probability":r"probab|bayes","hypothesis testing/p-value":r"hypothes|p-?value|significan","confidence intervals":r"confidence interval","A/B testing":r"a/b|experiment","power/sample size":r"power|sample size","correlation vs causation":r"correlat|causa","bias (sampling/selection)":r"bias","outliers/missing/data quality":r"outlier|missing|data quality|clean","KPIs/business metrics":r"metric|kpi","funnel/retention/churn/cohort":r"funnel|retention|churn|cohort","visualisation/chart choice/dashboards":r"visuali|chart|plot|dashboard","Power BI/DAX/Tableau":r"power ?bi|dax|tableau","SQL/Excel for analysis":r"excel|sql|pivot","regression interpretation":r"regress","time-series/forecasting/seasonality":r"time.?series|forecast|season","stakeholder communication/storytelling":r"stakeholder|storytell|communicat","segmentation/clustering":r"segment|cluster"})
R["coverage_keyword_heuristic"]=C
R["coverage_note"]="Keyword match on QUESTION text only (answers not searched). seed_questions = substantive Q&As; generated_topics = number of distinct template topic names matching (each backed by 12 templated Qs with no topic-specific content)."
# ---------- D. exposure: what share of questions an interview session can draw is template-generated?
R["template_share_by_difficulty_final"]={d:float((g_.src=="generated").mean()) for d,g_ in pj.groupby("difficulty")}
R["template_share_by_domain"]={d:float((g_.src=="generated").mean()) for d,g_ in pj.groupby("domain")}
R["seed_count_by_domain_x_final_difficulty"]=pd.crosstab(pj[pj.src=="seed"].domain,pj[pj.src=="seed"].difficulty).to_dict("index")
R["seed_count_by_domain_x_raw_difficulty"]=pd.crosstab(pj[pj.src=="seed"].domain,pj[pj.src=="seed"].raw_difficulty).to_dict("index")
R["all_count_by_domain_x_final_difficulty"]=pd.crosstab(pj.domain,pj.difficulty).to_dict("index")
# role -> domains (from config.py) exposure for Hard round
ROLE={"Data Scientist":["Machine Learning","Deep Learning","NLP","Data Analysis","Python"],"Machine Learning Engineer":["Machine Learning","Deep Learning","Python"],"NLP Engineer":["NLP"],"Data Analyst":["Data Analysis","Python"],"Python Developer":["Python"]}
R["role_pool_template_share_Hard"]={r:float((pj[pj.domain.isin(d)&(pj.difficulty=="Hard")].src=="generated").mean()) for r,d in ROLE.items()}
R["role_pool_seed_hard_count"]={r:int(((pj.src=="seed")&(pj.difficulty=="Hard")&pj.domain.isin(d)).sum()) for r,d in ROLE.items()}
R["role_pool_template_share_Easy"]={r:float((pj[pj.domain.isin(d)&(pj.difficulty=="Easy")].src=="generated").mean()) for r,d in ROLE.items()}
# ---------- E. benchmark overlap
import importlib.util,sys
sys.path.insert(0,str(root/"src/model"))
txt=open(root/"Temp/evaluate_models.py",encoding="utf-8").read()
cases_q=re.findall(r'"question":\s*(?:\'([^\']+)\'|"([^"]+)")',txt)
cq=[a or b for a,b in cases_q]
pjq=set(pj.question.map(norm_q))
R["evaluate_models_curated_question_count"]=len(cq)
R["evaluate_models_questions_present_verbatim_in_dataset"]=sum(norm_q(q) in pjq for q in cq)
R["evaluate_models_questions_list"]=cq
# Siamese training supervision: negatives drawn from same-domain template answers
an=pj.reference_answer
R["siamese_note"]="SiameseBiLSTM trains on every reference_answer (positive=itself) + 3 'negatives' (answer at index+17k) labelled 0.15 same-domain/0.0 cross-domain; ~89% of answers are template skeletons with mean TF-IDF cosine ~0.8 to each other -> noisy/contradictory supervision."
# ---------- F. answer-length vs difficulty for seed raw labels
R["seed_mean_answer_words_by_raw_difficulty"]=seed.groupby("raw_difficulty").aw.mean().round(1).to_dict()
R["seed_mean_answer_words_by_domain_raw_difficulty"]=seed.pivot_table(index="domain",columns="raw_difficulty",values="aw",aggfunc="mean").round(1).to_dict("index")
dump(out,"04_diversity_coverage.json",R)
print(json.dumps({k:v for k,v in R.items() if k not in("coverage_keyword_heuristic","seed_rows_with_any_serious_residue_ids")},indent=1,default=str)[:9000])
