"""Audit 6: manual review log. Verdicts were assigned by READING each Q&A (not automated).
Writes output/06_manual_review_log.csv and prints a summary. Selection: SQL + Python seed = full read (58);
ML/DL/NLP/DA = PURPOSIVE sample (targeted at suspicious/flagged items) -> defect rate must NOT be extrapolated."""
import csv, collections
from common import *
root,out=get_root()
L={}  # id -> (domain, verdict, defect_type, note)
def add(ids,dom,verdict,typ="",note=""):
    for i in ids: L[i]=(dom,verdict,typ,note)
# --- SQL (full read of all 30)
add(range(4028,4058),"SQL","ok_but_shallow","definition_only","one-line definition; no query/example")
add([4030],"SQL","defect","incomplete","FK answer omits referential integrity / referenced key")
add([4049],"SQL","defect","incomplete","RANK vs ROW_NUMBER: omits gap behaviour / DENSE_RANK; 'unique' only")
# --- Python (full read of all 28)
add(range(4058,4086),"Python","ok_but_shallow","prose_only","description without code")
add([4058,4059,4060,4062,4065,4067,4072],"Python","ok","","acceptable")
add([4061,4076],"Python","defect","placeholder","answer is generic filler: 'This question covers fundamental concepts...'")
add([4074],"Python","defect","does_not_address","asked 'with an example'; none given")
add([4066,4068,4069,4077,4080,4084,4085],"Python","defect","does_not_address","imperative 'Implement X' answered with prose, no code")
# --- ML (purposive: 25)
add([3754,3756,3779,3799,3822,3845,3883,3932,3935,3816],"Machine Learning","ok","","acceptable")
add([3843,3913,3921,3948,4013,4018],"Machine Learning","ok_but_shallow","short","very short / generic")
add([3765],"Machine Learning","defect","factual_minor","'maximum entropy gain' (should be information gain); loose Gini/entropy definitions; fragment question")
add([3862],"Machine Learning","defect","misleading","'R2 is independent of predictors' - R2 never decreases when predictors are added; wording garbled")
add([3899],"Machine Learning","defect","ambiguous_question","default split criterion is library-dependent (CART/sklearn=Gini; ID3/C4.5=entropy)")
add([3955],"Machine Learning","defect","does_not_address","'What is Kernel SVM?' answered with SVM-vs-logistic-regression advantages; identical to 3870")
add([3870],"Machine Learning","defect","duplicate_answer_unsupported_claim","answer identical to 3955; O(N^2K) vs O(N^3) claim unsupported")
add([3871],"Machine Learning","defect","loaded_question","presupposes XGBoost>SVM; superficial reasoning")
add([3915,3917],"Machine Learning","defect","unanswerable_company_specific","'our company' / 'our current data process' - no reference answer possible")
add([3769],"Machine Learning","defect","off_topic_bundle","'Confusion Metrics' answer bundles RMSE/MAE/R2; title typo")
# --- DL (purposive: 19)
add([3745,3738,3714],"Deep Learning","ok","","acceptable")
add([3730,3669,3661,3656],"Deep Learning","ok_but_shallow","short","short / generic")
add([3650],"Deep Learning","defect","incoherent_and_bleed","garbled 'special portrayal' text + embedded next question (9)")
add([3687],"Deep Learning","defect","incoherent","question/answer meaningless ('assumption structure')")
add([3733],"Deep Learning","defect","factually_wrong","bagging/boosting described incorrectly; not DL concepts")
add([3715],"Deep Learning","defect","muddled","'exploding gradient descent' not a term; 'clumps up the gradients'")
add([3659],"Deep Learning","defect","does_not_address","'How many layers' answered by listing input/hidden/output")
add([3670],"Deep Learning","defect","incorrect_absolute","'ReLU has to be used in hidden layers' - valid for non-negative regression outputs")
add([3739,3749,3751],"Deep Learning","defect","answer_bleed","answer contains subsequent numbered question(s) + 'Solution:' prefix")
add([3652,3732],"Deep Learning","defect","outdated","TF1-era / discontinued frameworks (Theano, Caffe2, CNTK, DyNetGensim run-together), 'Placeholders'")
add([3697],"Deep Learning","defect","outdated_and_editorial","outdated framework list + advice to candidate ('Make sure to answer...')")
# --- NLP (purposive: 12)
add([3982,3991,3975],"NLP","ok_but_shallow","vague_or_list","vague / list only")
add([3958],"NLP","defect","misleading","'stop words are useless... removal is one of the most important tasks' overclaims")
add([3973,3974],"NLP","defect","missing_content","'The below table shows...' - table lost; no content")
add([3981],"NLP","defect","missing_content","'Let us look at the formula...' - formula lost; blog editorial")
add([3993],"NLP","defect","question_typo","'What is NES?' (NER)")
add([3963,3967],"NLP","defect","does_not_address","how-to-with-library questions answered with definitions; no code")
add([3989],"NLP","defect","muddled","MLM description incoherent")
add([3966],"NLP","defect","irrelevant_ending","ends: 'implementation of POS tagging using stop words'")
# --- Data Analysis (purposive: 7)
add([3619,3620,3631],"Data Analysis","ok","","acceptable")
add([3630,3637],"Data Analysis","ok_but_shallow","short","short")
add([3628],"Data Analysis","defect","too_short","answer is '- PCA' (2 words)")
add([3633],"Data Analysis","defect","extraction_corruption","'wi data in your o ce' (lost ligatures) + weak answer")
rows=[(i,)+L[i] for i in sorted(L)]
with open(out/"06_manual_review_log.csv","w",newline="",encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["id","domain","verdict","defect_type","note"]); w.writerows(rows)
c=collections.Counter(r[2] for r in rows); byd=collections.defaultdict(collections.Counter)
for r in rows: byd[r[1]][r[2]]+=1
S={"reviewed_total":len(rows),"verdicts":dict(c),"by_domain":{k:dict(v) for k,v in byd.items()},
   "defect_types":dict(collections.Counter(r[3] for r in rows if r[2]=="defect")),
   "full_read_domains":{"SQL":30,"Python":28},"purposive_sample_domains":["Machine Learning","Deep Learning","NLP","Data Analysis"],
   "automated_residue_flags":{"flagged_content_damaging_union":20,"manually_adjudicated_false_positives":["3704 (content follows 'as shown below:')","3721 (content follows 'as shown below:')","3795 (regex matched '0. When AUC score is 0.')"],"confirmed":17}}
dump(out,"06_manual_review_summary.json",S); print(json.dumps(S,indent=1))
