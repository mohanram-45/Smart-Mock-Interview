"""Audit 3: AUTOMATED technical/quality checks. Output = flagged candidates only; every flag needs manual adjudication
(see manual review section of the report). Regexes are heuristics -> they can miss errors and can false-positive."""
import re, ast, sqlite3, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from common import *
root,out=get_root()
pj=pd.read_pickle(out/"processed_annotated.pkl").reset_index(drop=True)
seed=pj[pj.src=="seed"].copy()
R={}

# 1. text corruption (PDF ligature loss, hyphen breaks, mojibake)
CORR={"ligature_loss":r"\b(o ce|e ect|di erent|speci c|signi cant|e cient|su cient|bene t|de ne|identi|classi cation|rst\b|con dence|ex ibility)\b|\bwi data\b",
      "hyphen_break":r"\b\w{2,}- [a-z]{2,}\b","mojibake":r"â€|Ã.|�","double_space_or_tab":r"\t"}
R["corruption_seed"]={}
for k,rx in CORR.items():
    m=seed[seed.question.str.contains(rx,regex=True)|seed.reference_answer.str.contains(rx,regex=True)]
    R["corruption_seed"][k]={"n":len(m),"examples":[{"id":int(r.id),"snippet":(re.search(rx,r.question+" || "+r.reference_answer).group(0))} for _,r in m.head(8).iterrows()]}
# 2. placeholders / generic filler answers
PH=r"This question covers|including practical applications and best practices|A strong answer should|In interviews, the key is|a good candidate should"
R["placeholder_or_instructional_answers"]={"seed":int(seed.reference_answer.str.contains(PH,regex=True).sum()),
   "generated":int(pj[pj.src=="generated"].reference_answer.str.contains(PH,regex=True).sum()),"generated_total":int((pj.src=="generated").sum())}
# answers that are instructions to the candidate, not reference content ("A strong answer should ...")
R["generated_answers_that_describe_a_good_answer_instead_of_giving_one"]=R["placeholder_or_instructional_answers"]["generated"]

# 3. Q/A lexical relevance (seed)
tv=TfidfVectorizer(stop_words="english",sublinear_tf=True).fit(pj.question+" "+pj.reference_answer)
Qm=tv.transform(seed.question);Am=tv.transform(seed.reference_answer)
seed["qa_cos"]=np.asarray(Qm.multiply(Am).sum(axis=1)).ravel()
R["seed_qa_cosine_describe"]=seed.qa_cos.describe().round(3).to_dict()
low=seed.sort_values("qa_cos").head(25)
R["seed_lowest_qa_overlap"]=[{"id":int(r.id),"cos":round(r.qa_cos,3),"q":r.question[:110],"a":r.reference_answer[:160]} for _,r in low.iterrows()]
R["seed_zero_overlap_qa"]=int((seed.qa_cos==0).sum())

# 4. code / SQL presence vs "write/implement/query" questions
CODE_Q=r"\b(write|implement|code|query|program|script|create a function|how to implement|using python|using numpy|from scratch)\b"
code_like=r"(```|\bdef \w+\(|\bimport \w+|\bSELECT\b.+\bFROM\b|\bfor \w+ in\b|\bprint\()"
seed["is_code_q"]=seed.question.str.contains(CODE_Q,case=False,regex=True)
seed["has_code"]=seed.reference_answer.str.contains(code_like,regex=True)
R["seed_coding_style_questions"]=int(seed.is_code_q.sum())
R["seed_answers_containing_any_code_or_sql"]=int(seed.has_code.sum())
R["seed_coding_questions_with_code_in_answer"]=int((seed.is_code_q&seed.has_code).sum())
R["seed_coding_questions_without_code_examples"]=[{"id":int(r.id),"domain":r.domain,"q":r.question[:90]} for _,r in seed[seed.is_code_q&~seed.has_code].head(15).iterrows()]
R["generated_answers_containing_code_or_sql"]=int(pj[pj.src=="generated"].reference_answer.str.contains(code_like,regex=True).sum())
R["sql_domain_rows_with_executable_sql"]=int(pj[(pj.domain=="SQL")].reference_answer.str.contains(r"\bSELECT\b.+\bFROM\b",regex=True).sum())
# python syntax validate any fenced/def snippets (expected ~0)
bad=0;tot=0
for a in pj.reference_answer:
    for m in re.findall(r"```(?:python)?\n(.*?)```",a,re.S):
        tot+=1
        try: ast.parse(m)
        except SyntaxError: bad+=1
R["python_snippets_found_and_syntax_errors"]=[tot,bad]
sqlbad=0;sqltot=0
con=sqlite3.connect(":memory:")
for a in pj.reference_answer:
    for m in re.findall(r"(\bSELECT\b[^.;]{1,200}\bFROM\b[^;]*;?)",a,re.S):   # case-sensitive: avoids the English word "select"
        sqltot+=1
        try: con.execute("EXPLAIN "+m)
        except Exception as e:
            if "syntax" in str(e).lower(): sqlbad+=1
R["sql_snippets_found_and_syntax_errors"]=[sqltot,sqlbad]

# 5. suspect-claim scan (seed answers) -> manual adjudication list
CLAIMS={
 "precision_recall_formula_swap":r"precision[^.]{0,60}TP\s*/\s*\(?TP\s*\+\s*FN|recall[^.]{0,60}TP\s*/\s*\(?TP\s*\+\s*FP",
 "activation_range_wrong":r"sigmoid[^.]{0,60}(-1|−1)[^.]{0,20}(1)|tanh[^.]{0,60}0\s*(to|and)\s*1",
 "p_value_misread":r"p-?value[^.]{0,80}probability (that|of) the (null|alternative) (hypothesis )?is (true|false)",
 "ci_misread":r"95%[^.]{0,60}(probability|chance)[^.]{0,40}(true|population) (mean|value|parameter)",
 "type_error_swap":r"type (i|1) error[^.]{0,50}false negative|type (ii|2) error[^.]{0,50}false positive",
 "l1_l2_swap":r"(lasso|l1)[^.]{0,40}(squared|l2 penalty)|(ridge|l2)[^.]{0,40}(absolute|l1 penalty)",
 "outdated_tf1":r"tf\.Session|placeholder|tf\.contrib|TensorFlow 1|Theano|Caffe\b",
 "outdated_sklearn_py2":r"sklearn\.cross_validation|Imputer\b|Python 2\b|Variable\(",
 "sota_claims":r"state[- ]of[- ]the[- ]art",
 "absolute_claims":r"\b(always|never|best|guarantee[sd]?)\b",
 "bagging_boosting_in_dl":r"bagging and boosting",
}
R["claim_scan_seed"]={}
for k,rx in CLAIMS.items():
    m=seed[seed.reference_answer.str.contains(rx,case=False,regex=True)]
    R["claim_scan_seed"][k]={"n":len(m),"ids":m.id.astype(int).tolist()[:25]}
gen=pj[pj.src=="generated"]
R["claim_scan_generated_nonzero"]={k:int(gen.reference_answer.str.contains(rx,case=False,regex=True).sum()) for k,rx in CLAIMS.items()}

# 6. question quality (seed): heading-like / non-question forms
nq=seed[~seed.question.str.contains(r"\?\s*$|^(explain|define|describe|list|name|state|differentiate|implement|write|compare|how|what|why|when|which|given|you|say|let|suppose)",case=False,regex=True)]
R["seed_non_question_headings"]=[{"id":int(r.id),"q":r.question[:100]} for _,r in nq.head(20).iterrows()]
R["seed_non_question_headings_n"]=len(nq)
gramm=seed[seed.question.str.contains(r"^What is (decision trees|Kernel Functions|Support Vector Machines|Confidence Intervals)|^What (is|are) .*\b(functions|trees|machines|intervals)\?$",case=False,regex=True)]
R["seed_grammar_defects_what_is_plural_examples"]=[{"id":int(r.id),"q":r.question} for _,r in gramm.head(12).iterrows()]
# company-specific / unanswerable-by-reference
UNANS=r"\b(our company|your company|our current|your skills|us\b|for our)\b"
R["seed_company_specific_unanswerable"]=[{"id":int(r.id),"q":r.question[:100]} for _,r in seed[seed.question.str.contains(r"(our current|our company|use your machine learning skills|for our)",case=False,regex=True)].iterrows()]
# open-ended case questions (multiple valid answers)
OPEN=r"^(how would you|given |you are |you have |say that|say you|let's say|let’s say|what would be|what kind of|growth for|a certain metric|how could you)"
seed["open_case"]=seed.question.str.contains(OPEN,case=False,regex=True)
R["seed_open_ended_case_questions"]={"n":int(seed.open_case.sum()),"median_answer_words":float(seed[seed.open_case].aw.median()),"under_30_words":int((seed.open_case&(seed.aw<30)).sum())}
# answer length
R["seed_answers_under_20_words"]=int((seed.aw<20).sum()); R["seed_answers_under_10_words"]=int((seed.aw<10).sum())
R["seed_answers_under_20_words_by_domain"]=seed[seed.aw<20].domain.value_counts().to_dict()
R["seed_answer_over_150_words"]=int((seed.aw>150).sum())
# case: multiple-valid answers marker absent
R["has_any_field_marking_multiple_valid_answers"]=False
seed[["id","domain","raw_difficulty","difficulty","aw","qa_cos","open_case","is_code_q","has_code"]].to_csv(out/"03_seed_flags.csv",index=False)
dump(out,"03_accuracy_checks.json",R)
print(json.dumps({k:v for k,v in R.items() if k not in("seed_lowest_qa_overlap",)},indent=1,default=str)[:9500])
