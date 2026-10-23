"""Audit 1: integrity, lineage, template detection, difficulty rebalance effect."""
import re, collections, warnings
warnings.filterwarnings("ignore")
import pandas as pd
from common import *
root, out = get_root()
seed, exp, interim, pj, pc = load_all(root)
R = {}

# ---- stage counts
R["stage_counts"] = dict(raw_seed=len(seed), raw_expanded=len(exp), interim=len(interim),
                         processed_json=len(pj), processed_csv=len(pc))
R["json_csv_identical"] = bool((pj.reset_index(drop=True)[["id","domain","difficulty","question","reference_answer"]].astype(str)
                              .equals(pc[["id","domain","difficulty","question","reference_answer"]].astype(str))))
R["processed_domain_counts"] = pj.domain.value_counts().to_dict()
R["processed_difficulty_counts"] = pj.difficulty.value_counts().to_dict()
R["reported_matches"] = R["processed_domain_counts"] == {"Machine Learning":851,"Deep Learning":710,"NLP":649,"Python":628,"SQL":642,"Data Analysis":605}

# ---- provenance: tag each interim row as seed/generated (ingestion order = sorted csv: expanded first, then seed)
seed["src"]="seed"; exp["src"]="generated"
raw = pd.concat([exp, seed], ignore_index=True)   # sorted(glob): 'expanded...' < 'questions_seed'
raw["qn"]=raw.question.map(norm_q)
interim["qn"]=interim.question.map(norm_q)
pj["qn"]=pj.question.map(norm_q)
R["interim_rows_match_raw_rows"] = len(interim)==len(raw)
# positional alignment (ingestion preserves order); verify by question text
aligned = (interim.reset_index(drop=True).qn.values == raw.qn.values).mean() if len(interim)==len(raw) else None
R["interim_raw_positional_text_match_rate"]=float(aligned) if aligned is not None else None
interim["src"]=raw.src.values if len(interim)==len(raw) else "?"
interim["raw_difficulty"]=raw.difficulty.values if len(interim)==len(raw) else None
interim["raw_domain"]=raw.domain.values if len(interim)==len(raw) else None
interim["raw_id"]=raw.id.values if len(interim)==len(raw) else None

# ---- what did cleaning drop?
kept = set(pj.qn)
dropped = interim[interim.duplicated("qn")]   # cleaner drops later duplicates of an already-seen question
first_seen = interim.drop_duplicates("qn")
R["interim_to_processed_dropped"]=len(dropped)
R["dropped_by_src"]=dropped.src.value_counts().to_dict()
R["dropped_by_domain"]=dropped.domain.value_counts().to_dict()
# dropped = duplicates only?
dup_ct = interim.duplicated("qn").sum()
R["interim_exact_dup_questions(case-insens)"]=int(dup_ct)
R["dropped_equals_duplicates"]= int(len(dropped))==int(dup_ct)==(len(interim)-len(pj))
R["dropped_examples"]=dropped[["raw_id","src","domain","question"]].head(8).to_dict("records")
# which survived: attach src to processed
src_map = first_seen.set_index("qn")
pj["src"]=pj.qn.map(src_map.src); pj["raw_difficulty"]=pj.qn.map(src_map.raw_difficulty)
pj["raw_domain"]=pj.qn.map(src_map.raw_domain); pj["raw_id"]=pj.qn.map(src_map.raw_id)
R["processed_by_src"]=pj.src.value_counts().to_dict()
R["processed_domain_x_src"]=pd.crosstab(pj.domain,pj.src).to_dict("index")

# ---- empties / nulls / lengths
for name,df,acol in [("processed",pj,"reference_answer")]:
    R[f"{name}_empty_q"]=int((df.question.str.strip()=="").sum())
    R[f"{name}_empty_a"]=int((df[acol].str.strip()=="").sum())
    R[f"{name}_missing_fields"]=int(df[["id","domain","difficulty","question",acol]].isna().sum().sum())
R["processed_id_unique"]=bool(pj.id.is_unique); R["processed_id_sequential"]=bool((pj.id.values==range(1,len(pj)+1)).all())
R["raw_id_types"]={"seed":"integer 1..N (restarts per file)", "expanded":"string like ml_gen_0001"}
R["id_instability"]="processed ids are reassigned 1..N by DataCleaner each run; raw ids are discarded -> no stable key"
# ids: processed id vs raw id relationship
R["raw_id_dupes_across_files"]=int(pd.concat([seed.id,exp.id]).duplicated().sum())

# ---- answer duplication
pj["an"]=pj.reference_answer.map(lambda s:" ".join(s.lower().split()))
R["processed_exact_dup_answers_rows"]=int(pj.duplicated("an",keep=False).sum())
R["processed_unique_answers"]=int(pj.an.nunique())

# ---- templates in generated rows
TEMPLATES=[("Easy","What is {t} in {d}?"),("Easy","Why is {t} important in a real interview or project?"),
("Easy","What mistake do beginners often make with {t}?"),("Medium","How would you apply {t} in a realistic {d} workflow?"),
("Medium","How would you evaluate whether {t} was working correctly?"),("Medium","Compare {t} with a simpler alternative."),
("Medium","A project result looks suspicious after using {t}. How would you debug it?"),
("Medium","What interview follow-up would you expect after explaining {t}?"),("Medium","When would you avoid using {t}?"),
("Hard","Design an end-to-end solution that uses {t} under production constraints."),
("Hard","What are the main edge cases and failure modes for {t}?"),("Hard","How would you explain the trade-offs of {t} to a technical panel?")]
pats=[]
for i,(dif,tpl) in enumerate(TEMPLATES):
    rx="^"+re.escape(tpl).replace(r"\{t\}","(?P<t>.+?)").replace(r"\{d\}",r"(?P<d>Machine Learning|Deep Learning|NLP|Python|SQL|Data Analysis)")+"$"
    pats.append((i,dif,re.compile(rx)))
def match(q):
    for i,dif,rx in pats:
        m=rx.match(q)
        if m: return i,dif,m.group("t")
    return None,None,None
res=pj.question.map(match)
pj["tpl_id"]=[r[0] for r in res]; pj["tpl_orig_diff"]=[r[1] for r in res]; pj["topic"]=[r[2] for r in res]
pj["is_template_q"]=pj.tpl_id.notna()
R["seed_rows_matching_template_regex"]=int(((pj.src=="seed")&pj.is_template_q).sum())
R["template_question_rows_in_processed"]=int(pj.is_template_q.sum())
R["template_rows_by_domain"]=pj[pj.is_template_q].domain.value_counts().to_dict()
R["template_rows_all_from_generated_src"]=bool((pj[pj.is_template_q].src=="generated").all())
R["generated_rows_not_matching_templates"]=int(((pj.src=="generated")&~pj.is_template_q).sum())
R["distinct_template_topics_by_domain"]=pj[pj.is_template_q].groupby("domain").topic.nunique().to_dict()
R["distinct_template_topics_total"]=int(pj[pj.is_template_q].groupby(["domain","topic"]).ngroups)
R["share_template_rows"]=float(pj.is_template_q.mean())
# answer skeleton: strip topic & domain words => count distinct skeletons
def skel(row):
    a=row.reference_answer
    if row.topic: a=re.sub(re.escape(row.topic),"<T>",a,flags=re.I); a=re.sub(re.escape(row.topic.title()),"<T>",a)
    a=re.sub(r"core (Machine Learning|Deep Learning|NLP|Python|SQL|Data Analysis) concept related to .*?\. A strong","core <D> concept related to <CTX>. A strong",a)
    a=re.sub(r"in (Machine Learning|Deep Learning|NLP|Python|SQL|Data Analysis)\b","in <D>",a)
    a=re.sub(r"a (Machine Learning|Deep Learning|NLP|Python|SQL|Data Analysis) workflow","a <D> workflow",a)
    return " ".join(a.split())
t=pj[pj.is_template_q].copy(); t["skel"]=t.apply(skel,axis=1)
R["template_rows_distinct_answer_skeletons"]=int(t.skel.nunique())
R["template_answer_skeleton_counts_top"]=t.skel.value_counts().head(12).map(int).to_dict()
# mean words in template answers
R["template_answer_words_mean"]=float(t.reference_answer.map(wc).mean())
# fraction of template-answer content that is topic-specific: tokens in answer not in skeleton-common set
R["template_answer_contains_topic_specific_fact"]="0 of sampled -> see manual review; answers are instruction text + <topic> substitution"

# ---- DIFFICULTY: label rewriting
pj["diff_changed"]=pj.raw_difficulty!=pj.difficulty
R["difficulty_changed_by_cleaner_overall"]=int(pj.diff_changed.sum())
R["difficulty_changed_share"]=float(pj.diff_changed.mean())
R["difficulty_transition_raw_to_final"]=pd.crosstab(pj.raw_difficulty,pj.difficulty).to_dict("index")
R["difficulty_transition_raw_to_final_by_src"]={s:pd.crosstab(g.raw_difficulty,g.difficulty).to_dict("index") for s,g in pj.groupby("src")}
tt=pj[pj.is_template_q]
R["template_id_to_final_difficulty"]=pd.crosstab(tt.tpl_id,tt.difficulty).to_dict("index")
R["template_raw_difficulty_to_final"]=pd.crosstab(tt.tpl_orig_diff,tt.difficulty).to_dict("index")
# template ids that changed bucket
R["template_same_question_form_different_difficulty"]=int((tt.groupby("tpl_id").difficulty.nunique()>1).sum())
R["difficulty_final_share"]=(pj.difficulty.value_counts(normalize=True)).round(4).to_dict()
# complexity proxy: does final difficulty track answer length? (that's what the cleaner uses)
pj["aw"]=pj.reference_answer.map(wc); pj["qw"]=pj.question.map(wc)
R["mean_answer_words_by_final_difficulty"]=pj.groupby("difficulty").aw.mean().round(1).to_dict()
R["mean_answer_words_by_final_difficulty_seed_only"]=pj[pj.src=="seed"].groupby("difficulty").aw.mean().round(1).to_dict()
R["mean_answer_words_by_final_difficulty_template_only"]=tt.assign(aw=tt.reference_answer.map(wc)).groupby("difficulty").aw.mean().round(1).to_dict()
R["note"]="DataCleaner.rebalance_difficulties overwrites every label with a 30/45/25 quantile split on (word count + 25*keyword hits)."

# ---- domain relabelling in seed
R["seed_raw_domain_to_final"]=pd.crosstab(pj[pj.src=="seed"].raw_domain,pj[pj.src=="seed"].domain).to_dict("index")

# ---- answer-length stats
R["answer_words_describe_by_src"]={s:g.aw.describe().round(1).to_dict() for s,g in pj.groupby("src")}
R["answer_words_describe_seed_by_domain"]={d:g.aw.describe().round(1).to_dict() for d,g in pj[pj.src=="seed"].groupby("domain")}
R["answers_under_15_words_seed"]=int(((pj.src=="seed")&(pj.aw<15)).sum())
R["answers_over_300_words"]=int((pj.aw>300).sum())
R["processed_max_answer_words"]=int(pj.aw.max())

# ---- scraped-boilerplate / residue scan (seed)
RES={"blog_boilerplate":r"Next up on this|interview questions and answers blog|Click here|Subscribe|Read more|Edureka|Simplilearn|Intellipaat|©|copyright",
     "url":r"https?://|www\.","html":r"</?[a-z][^>]*>","embedded_difficulty":r"difficulty\s*level",
     "leading_enumeration_in_answer":r"^\s*(\d+[.)]|[-•*])\s","answer_label_leak":r"\b(Answer|Ans)\s*:","question_in_answer_start":r"^\s*(Q|Question)\s*[:.]"}
sd=pj[pj.src=="seed"]
R["seed_residue_counts"]={k:int((sd.reference_answer.str.contains(rx,case=False,regex=True)).sum()) for k,rx in RES.items()}
R["seed_question_residue_counts"]={k:int((sd.question.str.contains(rx,case=False,regex=True)).sum()) for k,rx in RES.items()}
R["seed_residue_examples"]={k:sd[sd.reference_answer.str.contains(rx,case=False,regex=True)][["id","question"]].head(3).to_dict("records") for k,rx in RES.items() if k in("blog_boilerplate","url","html")}
# questions not ending in ? / truncated
R["seed_questions_no_qmark_or_period"]=int((~sd.question.str.contains(r"[?.:]\s*$")).sum())
R["seed_questions_very_short(<4 words)"]=int((sd.qw<4).sum())
R["seed_questions_very_long(>60 words)"]=int((sd.qw>60).sum())
# answers ending abruptly
R["seed_answers_not_ending_in_punct"]=int((~sd.reference_answer.str.contains(r"[.!?)\]\"'`;]\s*$")).sum())
# seed dup (exact)
R["seed_exact_dup_questions_within_seed"]=int(seed.question.map(norm_q).duplicated().sum())
R["seed_vs_generated_exact_overlap"]=int(len(set(seed.question.map(norm_q))&set(exp.question.map(norm_q))))
# interim has same unique? 
R["unique_normalised_questions_processed"]=int(pj.qn.nunique())

pj.drop(columns=["an"]).to_pickle(out/"processed_annotated.pkl")
dump(out,"01_integrity.json",R)
print(json.dumps({k:R[k] for k in list(R)[:40]},indent=1,default=str)[:6000])
