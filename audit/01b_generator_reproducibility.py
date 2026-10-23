"""Audit 1b: does scripts/expand_interview_dataset.py (in memory only) reproduce data/raw/expanded_interview_questions.csv?"""
import importlib.util, io, contextlib
import pandas as pd
from common import *
root,out=get_root()
spec=importlib.util.spec_from_file_location("gen",root/"scripts/expand_interview_dataset.py"); g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
rows=[];seq=1
for dom,topics in g.DOMAINS.items():
    for t in topics:
        for dif,pat,ins in g.QUESTION_PATTERNS:
            rows.append((dom,dif,pat.format(topic=t,domain=dom),g.answer_for(dom,t,ins,dif))); seq+=1
gen=pd.DataFrame(rows,columns=["domain","difficulty","question","answer"])
exp=pd.read_csv(root/"data/raw/expanded_interview_questions.csv",dtype=str,keep_default_na=False)
R={"script_rows":len(gen),"csv_rows":len(exp),
   "script_topics_per_domain":{d:len(t) for d,t in g.DOMAINS.items()},
   "script_duplicate_topics_within_domain":{d:[t for t in set(ts) if ts.count(t)>1] for d,ts in g.DOMAINS.items()},
   "n_templates":len(g.QUESTION_PATTERNS)}
R["questions_identical_in_order"]=bool((gen.question.values==exp.question.values).all()) if len(gen)==len(exp) else False
R["question_set_equal"]=set(gen.question)==set(exp.question)
R["answer_set_equal"]=set(gen.answer)==set(exp.answer)
R["rows_in_csv_not_in_script_output"]=len(set(exp.question)-set(gen.question))
R["rows_in_script_not_in_csv"]=len(set(gen.question)-set(exp.question))
R["script_difficulty_counts"]=gen.difficulty.value_counts().to_dict()
R["csv_difficulty_counts"]=exp.difficulty.value_counts().to_dict()
R["csv_ids_prefix_sample"]=exp.id.head(3).tolist()+exp.id.tail(3).tolist()
dump(out,"01b_generator_reproducibility.json",R); print(json.dumps(R,indent=1))
