# Stage 1D - Batch 2 generation brief (Generative AI & RAG, part B). Read fully.

Project: SMART-MOCK-INTERVIEW knowledge base for later RAG use. You write ORIGINAL interview questions with reference answers. Domain for every record: **Generative AI & RAG**. This batch covers cells GEN-08 .. GEN-15 (see /home/claude/work/b2/cells_b2.json; you are told which cells are yours). Quality beats quantity: if you cannot write a genuinely distinct, technically solid question for a slot, write fewer and say why; never pad.

## Hard rules
1. Technical correctness over everything. If unsure a statement is true, remove it or state the condition under which it holds. Do not invent facts, numbers, benchmarks, citations or URLs. Hedge contested empirical claims ("often", "in many setups", "model-dependent").
2. NEVER claim or imply a question was asked in a real interview or by a named company.
3. No time-sensitive facts: no model names/versions as facts, no benchmark scores, no vendor limits, prices or quotas. Explain mechanisms instead. If a question must touch a fast-changing area set `time_sensitive: true`.
4. Questions are self-contained, specific and realistic (concrete numbers, symptoms, a described pipeline), answerable in an interview. No generic templates ("Explain X in the context of Y"). At most ~35% of your questions may start with "What is / What are / Explain". Each must differ in intent from every item in /home/claude/work/b2/existing_questions.json (533 existing questions: v5 plus accepted batch 1) AND from every other record in the batch.
5. Prefer conceptual, scenario, debugging and evaluation questions. Use coding only where the cell says tested example. Do not turn a concept question into a coding question.
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
Batch 1 needed a separate source pass and it caught 14 overstatements. Do it up front. For every factual comparison, documented behaviour, default value, algorithm property, paper result and design recommendation, open an authoritative page (official documentation, the original paper) with WebFetch, and write the sentence so that it says no more than the page supports. List a source only if you opened it and its text supports the specific sentence as worded (`supports`); otherwise hedge the sentence ("in many setups", "often") or drop it. Never cite from memory, never cite a blog when an official page exists, never add a citation just to have one. Mechanism/arithmetic questions verified by executed code or derivation need no source. If WebFetch is refused, leave `sources` empty and hedge. The lead and independent verifiers will re-open every URL.
Hard rule for this domain: no model names or versions, no vendor limits/prices/quotas, no API parameter lists presented as current fact. Describe mechanisms. Mark `time_sensitive: true` where the area changes fast.
Question style: at most 3 questions in the batch may contain "What is/What are/Explain"; vary the openings; include concrete hypothetical numbers or a described system. For the safety cell: defensive mechanisms only, no working attack payloads.

## Output
Write ONE JSON list to the path given. One object per question:
{
 "plan_id": "B2-<cell_id>-<n>"   // e.g. B2-GEN-09-2
 "cell_id": "GEN-03", "topic": "<the cell topic text>",
 "domain": "Generative AI & RAG",
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
