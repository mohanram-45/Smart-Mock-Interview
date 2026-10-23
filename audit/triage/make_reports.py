import pandas as pd, json, re, warnings
warnings.filterwarnings('ignore')
from gap_concepts import C, REF
OUT='/home/claude/work/out/data/audit/'
df=pd.read_pickle('triage_df.pkl'); s=df[df.source_type=='seed'].copy()
s['dom']=s.apply(lambda r: r.proposed_domain or r.domain,axis=1)
DOMS=['Machine Learning','Deep Learning','NLP','Python','SQL','Data Analysis']
ST=['KEEP','FIX','EXCLUDE','EXCLUDE_TEMPLATE']
def tbl(frame,col='domain'):
    ct=pd.crosstab(frame[col],frame.status).reindex(index=DOMS,columns=ST,fill_value=0)
    ct['Total']=ct.sum(axis=1); ct.loc['**All**']=ct.sum()
    lines=['| Domain | KEEP | FIX | EXCLUDE | EXCLUDE_TEMPLATE | Total |','|---|---:|---:|---:|---:|---:|']
    for d,r in ct.iterrows(): lines.append(f'| {d} | '+' | '.join(str(int(r[c])) for c in ST+['Total'])+' |')
    return '\n'.join(lines)
fx=s[s.status=='FIX']
flags=s['flags'].str.split(';').explode(); flags=flags[flags!='']
rs=fx.review_state.value_counts()
dchg=s[(s.proposed_difficulty!='')]
n_diff_cur=(dchg.proposed_difficulty!=dchg.difficulty).sum(); n_diff_raw=(dchg.proposed_difficulty!=dchg.raw_difficulty).sum()
dom_moves=s[(s.proposed_domain!='')&(s.proposed_domain!=s.domain)]
code=s[s.code_test!='NA'].code_test.value_counts().to_dict()
dupc=s[s.duplicate_of!='']
chain=dupc[dupc.duplicate_of.apply(lambda t: s.loc[s.id==t,'status'].iloc[0]=='EXCLUDE')]
cos_keep=s[(s.status=='KEEP')&s['flags'].str.contains('COSMETIC_PREFIX')]
summary=f'''# Dataset triage summary

Scope: all {len(df):,} records in `data/processed/questions.csv` (processed IDs preserved). Nothing in the original datasets, pipeline code or models was modified; every status below is a *proposal* awaiting approval.

## 1. Counts by domain (all records, current domain labels)

{tbl(df)}

* **EXCLUDE_TEMPLATE (3,618)**: every record produced by `scripts/expand_interview_dataset.py` (processed IDs 1-3618).
* **Seed records (467)**: KEEP {int((s.status=='KEEP').sum())}, FIX {int((s.status=='FIX').sum())}, EXCLUDE {int((s.status=='EXCLUDE').sum())}.

### Seed records only

{tbl(s)}

### Seed records if proposed domain moves were applied ({len(dom_moves)} records)

{tbl(s,'dom')}

Domain moves are all *proposals* (Predictive-modelling product-metric cases to Data Analysis; one ML-labelled deep-learning definition to Deep Learning). Statistics questions (Central Limit Theorem, confidence intervals, hypothesis tests) currently sit in ML and could move to Data Analysis if you want that domain to cover statistics; see `gap_analysis.md`.

## 2. FIX records ({len(fx)}) by review state

| review_state | Count | Meaning |
|---|---:|---|
| ready_for_approval | {rs.get('ready_for_approval',0)} | Mechanical fix (trim of leaked text, typo) or rewrite that uses only well-established facts; still needs your sign-off |
| needs_review | {rs.get('needs_review',0)} | Proposal depends on judgement (domain move, premise change, contested claim, missing table reconstructed from general knowledge) |
| needs_code_test | {rs.get('needs_code_test',0)} | Needs executable verification that could not be completed here |
| needs_source | {rs.get('needs_source',0)} | Technically uncertain; no proposal made (3834, temporal-difference learning) |

Proposal confidence (reviewer judgement): high {int((fx.proposal_confidence=='high').sum())}, medium {int((fx.proposal_confidence=='medium').sum())}, low {int((fx.proposal_confidence=='low').sum())}. {int(((fx.proposed_question=='')&(fx.proposed_answer=='')&(fx.proposed_domain=='')).sum())} FIX records have **no proposed text** because I could not responsibly invent one (IDs: {', '.join(str(i) for i in fx[(fx.proposed_question=='')&(fx.proposed_answer=='')&(fx.proposed_domain=='')].id)}).

## 3. What was found in the 467 seed records

| Flag | Records |
|---|---:|
''' + '\n'.join(f'| {k} | {v} |' for k,v in flags.value_counts().head(24).items()) + f'''

(A record can carry several flags. THIN_ANSWER on a KEEP record means the answer is correct but brief.)

Requested categories:

* **Corrupted answers**: {int(s['flags'].str.contains('CORRUPTED').sum())} flagged CORRUPTED, plus {int(s['flags'].str.contains('ANSWER_BLEED').sum())} with next-question text leaked into the answer and {int(s['flags'].str.contains('FACTUAL_ERROR').sum())} with a factual error.
* **Missing formulas**: {int(s['flags'].str.contains('MISSING_FORMULA').sum())}; **missing tables**: {int(s['flags'].str.contains('MISSING_TABLE').sum())} (3973, 3974, 3990); **outdated content**: {int(s['flags'].str.contains('OUTDATED').sum())}.
* **Questions requiring executable code**: {int(s['flags'].str.contains('REQUIRES_CODE').sum())} (REQUIRES_CODE) and {int(s['flags'].str.contains('REQUIRES_DATA').sum())} requiring an external dataset (REQUIRES_DATA).
* **Duplicates**: {len(dupc)} seed records are marked as duplicates of another seed record (`duplicate_of`); {len(chain)} of those point at a record that is itself excluded (the whole cluster is excluded as low value: {', '.join(f'{r.id}->{r.duplicate_of}' for r in chain.itertuples())}).
* **Difficulty**: reviewer rubric (Easy = single-concept recall, Medium = comparison/mechanism/application, Hard = multi-step reasoning/design/edge cases) was applied to the {len(dchg)} KEEP/FIX records. The proposed label differs from the current processed label in {int(n_diff_cur)} cases ({n_diff_cur/len(dchg):.0%}) and from the *raw* seed label in {int(n_diff_raw)} ({n_diff_raw/len(dchg):.0%}). Difficulty changes are recorded in `proposed_difficulty` only; they do not by themselves make a record FIX.
* **Cosmetic prefixes** ("Ans.", "Solution:") remain on {len(cos_keep)} KEEP records; they are stripped in proposed answers of FIX records only. Recommended as a pipeline normalisation step.

### Executable-code verification

Snippets proposed for answers were run in the audit sandbox (Python 3, NumPy, matplotlib, NLTK 3 installed into a scratch directory): **{code.get('PASS',0)} passed**, {code.get('FAIL_OR_NOT_RUNNABLE',0)} could not be run (3963: NLTK tokenizer data cannot be downloaded in the sandbox). {code.get('NOT_TESTED',0)} records that need code (4075 Flask REST, 4077 JWT, 4081 pytest mocking, 3967 spaCy similarity) have **no proposed answer** because pytest/spaCy are not installed and the Flask/JWT items are security- and scope-sensitive. Passing tests mean the snippet behaves as described; they do not remove the need for human approval.

## 4. How the generated records were handled

All 3,618 generated rows are EXCLUDE_TEMPLATE without individual review. They come from 304 (domain, topic) pairs x 12 question templates; once the topic is masked the answers collapse to 15 distinct texts, difficulty labels are produced by a keyword-count rebalance, and the answers describe what a good answer should contain rather than giving one (see `reports/dataset_audit.md`). Their `note` column carries this reason.

## 5. Usable pool for RAG

KEEP + ready_for_approval FIX = **{int((s.status=='KEEP').sum()+((s.status=='FIX')&(s.review_state=='ready_for_approval')).sum())}** seed questions; KEEP + all FIX = {int((s.status=='KEEP').sum()+(s.status=='FIX').sum())}. Many KEEP answers are one-line definitions, so even the best case is a small, thin reference set (see `gap_analysis.md`).

## 6. Files

* `data/audit/triage.csv`: one row per record (4,085), original question and answer plus proposed fields.
* `data/audit/triage_summary.md` (this file), `proposed_corrections.md`, `gap_analysis.md`, `unresolved_issues.md`.
* `audit/triage/`: decision files (`dec_*.py`), builders and test runner.
'''
open(OUT+'triage_summary.md','w',encoding='utf-8').write(summary)

# ---------- proposed corrections
def blk(r):
    o=[f'### {r.id}  (raw {r.raw_id}; {r.domain}; current {r.difficulty}, raw {r.raw_difficulty})',
       f'* **Review state:** {r.review_state}; **confidence:** {r.proposal_confidence or "n/a"}; **flags:** {r["flags"]}',
       f'* **Issue:** {r.note}']
    if r.proposed_difficulty and r.proposed_difficulty!=r.difficulty: o.append(f'* **Proposed difficulty:** {r.proposed_difficulty}')
    if r.proposed_domain: o.append(f'* **Proposed domain:** {r.proposed_domain}')
    o.append(f'* **Original question:** {r.question}')
    if r.proposed_question: o.append(f'* **Proposed question:** {r.proposed_question}')
    o.append(f'* **Original answer:** {r.reference_answer}')
    if r.proposed_answer: o.append(f'* **Proposed answer ({r.proposal_basis}):** {r.proposed_answer}')
    else: o.append('* **Proposed answer:** none proposed' + (' (answer unchanged)' if r.proposed_question or r.proposed_domain else ''))
    if r.code_test!='NA': o.append(f'* **Code test:** {r.code_test}')
    return '\n'.join(o)
pc=['# Proposed corrections','',f'{len(fx)} FIX records. Nothing here has been applied. Grouped by review state; IDs are processed IDs, `raw_id` is the id in `questions_seed.csv`. Proposed answers are drafts written for review: "ready_for_approval" means the change uses well-established facts or a mechanical edit, not that it is approved.','']
for stt,title in [('ready_for_approval','A. Ready for approval'),('needs_review','B. Needs review (judgement involved)'),('needs_code_test','C. Needs code test'),('needs_source','D. Needs a source')]:
    sub=fx[fx.review_state==stt].sort_values('id')
    pc.append(f'## {title} ({len(sub)})'); pc.append('')
    for r in sub.itertuples(): pass
    for _,r in sub.iterrows(): pc.append(blk(r)); pc.append('')
open(OUT+'proposed_corrections.md','w',encoding='utf-8').write('\n'.join(pc))

# ---------- gap analysis
pool=s[s.status.isin(['KEEP','FIX'])].copy()
pool['qtxt']=(pool.proposed_question.where(pool.proposed_question!='',pool.question)).str.lower()
ga=['# Domain gap analysis','',
 'Method: for each domain a checklist of core interview concepts (drawn from standard curricula, not from the dataset) was matched by keyword against the **question text of the 367 KEEP/FIX seed records** (using proposed domain and proposed question where present). A hit count is only a coverage indicator: a hit does not mean the answer is good (many are one-liners) and 0 does not prove absence, but 0-1 hits is treated as a gap. Generated template questions are ignored because they repeat 304 topics with 12 fixed phrasings.','',
 'Reference sources are suggestions for a human curator to evaluate. **Licences and terms of use were not verified**; do not ingest text from any of them until the licence has been checked. No new questions were generated.','']
for d in DOMS:
    sub=pool[pool.dom==d]
    ga.append(f'## {d}  ({len(sub)} KEEP/FIX seed questions)'); ga.append('')
    ga.append('| Concept | Hits | Gap? |'); ga.append('|---|---:|---|')
    miss=[]
    for c,rx in C[d]:
        n=int(sub.qtxt.str.contains(rx,regex=True).sum()); g='**gap**' if n<=1 else ('thin' if n<=3 else '')
        if n<=1: miss.append(c)
        ga.append(f'| {c} | {n} | {g} |')
    ga.append('')
    ga.append(f'**Missing or near-missing ({len(miss)}):** '+('; '.join(miss) if miss else 'none by this checklist')+'.'); ga.append('')
    ga.append('**Suggested reference sources (licences unverified):** '+'; '.join(REF[d])+'.'); ga.append('')
ga+=['## Cross-cutting observations','',
 '* Statistics (hypothesis testing, confidence intervals, CLT, Bayes) is represented only inside ML; the Data Analysis domain has almost no seed content of its own once the product-metric cases are counted. Decide where statistics should live before curating.',
 '* The seed set has no hands-on exercises with a schema/dataset and expected output (SQL queries, pandas transforms), which is what a code-aware interviewer or RAG grounding needs.',
 '* Modern topics (transformers, embeddings, BERT/GPT, fine-tuning, RAG, LLM evaluation) are largely absent from the seed set; the audit found the same in the generated set.',
 '* Per the constraints, this document identifies gaps only; it does not propose question text.']
open(OUT+'gap_analysis.md','w',encoding='utf-8').write('\n'.join(ga))

# ---------- unresolved issues
un=['# Unresolved issues','']
def lst(ids): return ', '.join(str(i) for i in ids)
nop=fx[(fx.proposed_question=='')&(fx.proposed_answer=='')&(fx.proposed_domain=='')]
un+=['## 1. FIX records with no proposed text','']
for _,r in nop.iterrows(): un.append(f'* **{r.id}** ({r.review_state}, {r.proposal_confidence}): {r.question[:110]}  - {r.note}')
un+=['','## 2. Technically uncertain proposals (not auto-approved)','',
 'All records in state `needs_review` ('+str(int((fx.review_state=="needs_review").sum()))+'), in particular: 3803 (correlated features), 3809 (global minimum / domain), 3810 (sparse data), 3813 (dimensionality reduction before SVM), 3858 (item-based CF), 3871 (XGBoost vs SVM), 3961 (semantic analysis), 3985 (NLTK vs spaCy), 3988 (pragmatic ambiguity), 3973/3974 (reconstructed from general knowledge because the tables are missing), 3965 (stemmer output verified with NLTK; wording needs a reviewer).','',
 '## 3. Judgement calls you may want to overrule','',
 f'* LOW_RELEVANCE exclusions: {lst(s[s["flags"].str.contains("LOW_RELEVANCE")&(s.status=="EXCLUDE")].id)}.',
 '* Legacy-topic exclusions (Boltzmann machines, DBN framing, TensorFlow 1.x): 3675, 3708, 3719, 3723, 3732.',
 '* Open-ended case questions kept with THIN_ANSWER (4002-4025 range): the questions are classic but the answers are one-line outlines; they will not support grounded answers.',
 '* Behavioural / company-specific questions (3915-3917) excluded or rewritten.','',
 '## 4. Process issues','',
 f'* {len(chain)} duplicate links point to an excluded record, so no canonical survivor exists for those clusters: {", ".join(f"{r.id}->{r.duplicate_of}" for r in chain.itertuples())}.',
 '* Duplicate detection among seed records used my reading plus the turn-1 TF-IDF audit; a final pass over KEEP+FIX pairs after approval is recommended (e.g. overlaps between 3794/3864/4000-type regularisation items, 3779/3944, 3939 and the DL SGD item).',
 f'* {len(cos_keep)} KEEP records still carry "Ans."/"Solution:" prefixes.',
 f'* Domain labels: {len(dom_moves)} proposed domain moves; the pipeline maps raw PREDICTIVE_MODELLING to ML, so moves require a mapping decision.',
 '* Difficulty labels for the whole set remain unreliable: the pipeline rebalance rewrites 44% of them; proposed difficulties are reviewer judgement and unvalidated.',
 '* The rebalanced difficulty and the Siamese baseline were trained on template pairs; no model was retrained or re-evaluated here.',
 '','## 5. Not done (by design)','',
 '* No original file or production code was modified; no model retrained; no FAISS/RAG work; no new questions generated.']
open(OUT+'unresolved_issues.md','w',encoding='utf-8').write('\n'.join(un))
print('ok')
