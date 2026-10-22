# Stage 1D - Batch 1 generation brief (Generative AI & RAG, part A). Read fully.

Project: SMART-MOCK-INTERVIEW knowledge base for later RAG use. You write ORIGINAL interview questions with reference answers. Domain for every record: **Generative AI & RAG**. This batch covers cells GEN-01 .. GEN-07 (see /home/claude/work/b1/cells_b1.json; you are told which cells are yours). Quality beats quantity: if you cannot write a genuinely distinct, technically solid question for a slot, write fewer and say why; never pad.

## Hard rules
1. Technical correctness over everything. If unsure a statement is true, remove it or state the condition under which it holds. Do not invent facts, numbers, benchmarks, citations or URLs. Hedge contested empirical claims ("often", "in many setups", "model-dependent").
2. NEVER claim or imply a question was asked in a real interview or by a named company.
3. No time-sensitive facts: no model names/versions as facts, no benchmark scores, no vendor limits, prices or quotas. Explain mechanisms instead. If a question must touch a fast-changing area set `time_sensitive: true`.
4. Questions are self-contained, specific and realistic (concrete numbers, symptoms, a described pipeline), answerable in an interview. No generic templates ("Explain X in the context of Y"). At most ~35% of your questions may start with "What is / What are / Explain". Each must differ in intent from every item in /home/claude/work/b1/existing_questions.json (487 existing questions) AND from every other record in the batch.
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

## Sources
List a source only if you opened it with WebFetch/WebSearch in this task and it supports the specific sentence (`supports`). If fetching is refused, leave `sources` empty and hedge accordingly - that is acceptable and honest. Do not cite from memory. (The lead will open sources again independently.)

## Output
Write ONE JSON list to the path given. One object per question:
{
 "plan_id": "B1-<cell_id>-<n>"   // e.g. B1-GEN-03-2
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
