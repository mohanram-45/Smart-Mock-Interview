# Stage 1D - Batch 4 generation brief (MLOps & Model Deployment, part B). Read fully.

Project: SMART-MOCK-INTERVIEW knowledge base for later RAG use. You write ORIGINAL interview questions with reference answers. Domain for every record: **MLOps & Model Deployment**. This batch covers cells MLO-08 .. MLO-14 (see /home/claude/work/b4/cells_b4.json; you are told which cells are yours). Quality beats quantity: if you cannot write a genuinely distinct, technically solid question for a slot, write fewer and say why; never pad.

## Hard rules
1. Technical correctness over everything. If unsure a statement is true, remove it or state the condition under which it holds. Do not invent facts, numbers, benchmarks, citations or URLs. Hedge contested empirical claims ("often", "in many setups", "model-dependent").
2. NEVER claim or imply a question was asked in a real interview or by a named company.
3. No time-sensitive facts: no model names/versions as facts, no benchmark scores, no vendor limits, prices or quotas. Explain mechanisms instead. If a question must touch a fast-changing area set `time_sensitive: true`.
4. Questions are self-contained, specific and realistic (concrete numbers, symptoms, a described pipeline), answerable in an interview. No generic templates ("Explain X in the context of Y"). At most ~35% of your questions may start with "What is / What are / Explain". Each must differ in intent from every item in /home/claude/work/b4/existing_questions.json (626 existing questions: v5 plus accepted batches 1-3). Also read /home/claude/work/b4/mlops_existing.txt (59 existing MLOps-related questions incl. all of Batch 3: you must not repeat their intent) AND from every other record in the batch.
5. Prefer a balanced mix of conceptual, scenario, debugging, system-design and business-impact questions. Use coding only where the cell says tested example. Do not turn a concept question into a coding question.
6. Difficulty by actual content only: Easy = single-concept recall (short question, answer fits ~80-150 words); Medium = comparison, mechanism, short code or application; Hard = multi-step reasoning, design with trade-offs, subtle debugging or non-trivial implementation. Do not balance counts and do not inflate.

## Answer formats (new schema) - use only what adds distinct value
Choose `answer_set` per record: `single` | `concise+detailed` | `detailed+practical` | `concise+detailed+practical`.
* `single`: put the one reference answer in `answer` (direct answer first, then reasoning, conditions, pitfalls; 80-350 words). Leave the three other answer fields null.
* Multi-field sets: put NOTHING in `answer`; fill exactly the fields named in `answer_set`.
  * `concise_answer`: interview-ready, MAX 80 words, answer stated first.
  * `detailed_answer`: rigorous reference explanation, 120-450 words, with mechanism, conditions and pitfalls. Always present in a multi-field set (it becomes the canonical `answer`).
  * `practical_answer`: a worked scenario, configuration, procedure or code that is NOT already in the detailed answer. Must not merely paraphrase another field.
* Never create a variant just to have more fields. Definitions and simple recall usually stay `single` or `concise+detailed`. A rough target for the batch is ~40% multi-field, ~15% with all three. Numbers must agree across all fields of a record.
* Fenced code: if code is tested, the code fenced in the answer fields must be IDENTICAL to the tested `solution` (put the fence in exactly one field, normally `practical_answer` or `detailed_answer`).

## Executable code (only where useful)
* Any numeric claim you compute and any code shown must have been RUN by you. Numeric expectations come from executing code, never from memory.
* Recorded code (`solution` and `test`) must use ONLY the Python standard library and numpy (owner's stack: Python 3.10, numpy 2.2; no Python 3.11+ features; no network; no wall-clock timing; deterministic seeds). Test on /home/claude/work/dep/v/bin/python (3.13; it also has rank_bm25, faiss-cpu for cross-checking only), on /home/claude/work/v310/bin/python and on /home/claude/work/v311/bin/python (numpy 2.2.6, pandas 2.3.3). You may cross-check your implementation against rank_bm25 / faiss in the dep venv, but the recorded code may not import them.
* `code` = {"language":"python","setup":"","solution":"...","test":"asserts that import/execute the solution","expected":null}. The `test` is appended after `solution` in one file and must exit 0.

## Sources (stricter than batch 1)
Batches 1-2 needed a separate source pass that caught many overstatements; the target for this batch is meaningful source support for at least 70% of records, so write questions whose key claims are documented (official docs, original papers such as 'Hidden Technical Debt in Machine Learning Systems', 'The ML Test Score', Google's 'Rules of Machine Learning') and open those pages up front. Never pad. For every factual comparison, documented behaviour, default value, algorithm property, paper result and design recommendation, open an authoritative page (official documentation, the original paper) with WebFetch, and write the sentence so that it says no more than the page supports. List a source only if you opened it and its text supports the specific sentence as worded (`supports`); otherwise hedge the sentence ("in many setups", "often") or drop it. Never cite from memory, never cite a blog when an official page exists, never add a citation just to have one. Mechanism/arithmetic questions verified by executed code or derivation need no source. If WebFetch is refused, leave `sources` empty and hedge. The lead and independent verifiers will re-open every URL.
Hard rule for this domain: no version numbers, no vendor limits/prices/quotas, no CLI/API flag lists presented as current fact. Tool names (MLflow, DVC, Kubernetes, Docker, ONNX, Feast, TFX...) may be used as examples ONLY where you opened the official documentation and describe documented behaviour; otherwise keep it tool-agnostic. Describe mechanisms. Mark `time_sensitive: true` where the area changes fast.
Question style: at most 5 questions in the batch may start with "What is/What are/Explain" (introductory Easy questions are welcome where the subject warrants them; difficulty by content only); vary the openings; include concrete hypothetical numbers or a described system for scenario/debugging/design questions.

## Output
Write ONE JSON list to the path given. One object per question:
{
 "plan_id": "B4-<cell_id>-<n>"   // e.g. B4-MLO-04-2
 "cell_id": "GEN-03", "topic": "<the cell topic text>",
 "domain": "MLOps & Model Deployment",
 "status": "ok" | "defer",
 "question_type": "concept"|"scenario"|"debugging"|"coding"|"design"|"evaluation"|"business_case",
 "difficulty": "Easy"|"Medium"|"Hard",
 "question": "...",
 "answer_set": "single"|"concise+detailed"|"detailed+practical"|"concise+detailed+practical",
 "answer": null|"...", "concise_answer": null|"...", "detailed_answer": null|"...", "practical_answer": null|"...",
 "key_concepts": ["3-8 specific terms, each discussed in the answer; no generic words, no duplicates"],
 "common_mistakes": ["1-3 genuine typical wrong answers/pitfalls"],
 "interview_style_note": "one line on what a strong candidate demonstrates (used for grading)",
 "code": null | {...},
 "sources": [{"title","url","supports"}],
 "related_domains": ["NLP", ...] // optional, only real overlaps
 "tags": ["..."],
 "time_sensitive": false,
 "change_notes": "design intent of the question / why it is distinct from the nearest existing question (name its id)",
 "confidence": "high"|"medium"|"low"
}
After writing, print counts (ok/defer, by cell, by answer_set, code executed and results). Modify no file other than your output.


## Batch 4 additions (read carefully)
* Cells MLO-08..MLO-14 (count 41 total). Batch 3 already covered: reproducibility, CI/CD promotion gate, registry/packaging, serving patterns and serving-layer SLIs, deployment strategies (shadow/canary/A-B/blue-green), containers/K8s probes/GPU scheduling, feature stores/skew. Your questions must add NEW intent (see mlops_existing.txt); for MLO-12 and MLO-14 take the incident/diagnosis/rollback/cost/business angle on those topics rather than re-explaining them.
* Configuration examples (YAML, Dockerfile): put each in a top-level `configs` list: {"lang":"yaml"|"dockerfile"|"sql","content":"...","note":"what it demonstrates"} and fence it in exactly one answer field using ```yaml / ```dockerfile / ```sql with IDENTICAL content. Prefer COMPLETE Kubernetes objects (e.g. a full Deployment/Pod/HorizontalPodAutoscaler with apiVersion, kind, metadata, spec) instead of fragments so the offline schema validator (kubernetes-validate, k8s 1.31 schema) can check them; run /home/claude/work/proj/audit/expansion/config_check.py logic yourself (python3 with yaml, kubernetes_validate, dockerfile_parse installed) before submitting. Dockerfiles are only syntax-parsed (no Docker daemon), say nothing that claims they were built. Use placeholders for image digests. Do not put config in an answer unless it adds value.
* SQL: any SQL shown must be executed with Python's sqlite3 (SQLite dialect; say so) against a small in-memory dataset inside the recorded `code.test`; the fenced SQL must equal the string constant `SQL = """..."""` used by the code (put the same text in `configs` with lang "sql"). Result values stated in the answer come from that run.
* Python code rules unchanged (stdlib + numpy; tested on 3.13/3.10/3.11); fenced python == tested solution.
* Security/governance (MLO-11): engineering controls only, no legal advice; hedge with "depends on jurisdiction and legal advice"; no regulation article numbers unless you opened the official text.
* Include 1-3 genuinely introductory Easy questions across the batch where the subject warrants (e.g. data drift vs concept drift, what continuous training means, what a model card is) - difficulty by content, never forced.
* Sources: 70% target, official docs/papers only, opened by you before citing, supports-sentence worded narrowly. Useful authoritative pages: Google SRE book/workbook, Google 'Rules of Machine Learning', 'Hidden Technical Debt in ML Systems', 'The ML Test Score', 'Monitoring ML models in production' type vendor docs ONLY if official (e.g. Vertex AI/SageMaker Model Monitor docs), MLflow docs, Kubernetes docs, Python docs (pickle security), NIST AI RMF (nist.gov), Model Cards for Model Reporting (arXiv 1810.03993), 'Datasheets for Datasets', GDPR text (eur-lex) only if opened, OWASP ML Security / LLM Top 10 (owasp.org), PSI/KS definitions via scipy docs for ks_2samp, Evidently/other OSS docs only for documented behaviour. If a page cannot be opened leave out the claim or hedge it.
* Add to each record: "configs": [] when none. Everything else in the output schema is unchanged.
