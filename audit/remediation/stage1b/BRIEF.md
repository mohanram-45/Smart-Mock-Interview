# Stage 1B shared brief (read fully)

Project: SMART-MOCK-INTERVIEW interview knowledge base, built for later RAG use. Records are interview questions with reference answers.
Python 3.13 sandbox with numpy, pandas, scikit-learn, spaCy (+ en_core_web_md), nltk (no punkt data: network blocks it), pytest, sqlite3 (SQLite 3.45). No torch/tensorflow. Shell has no general internet; use WebFetch/WebSearch for docs.

## Hard rules
1. Technical correctness over everything. If you are not sure a statement is true, remove it or state the condition under which it holds. Do not pad. Do not invent facts, numbers, benchmarks, citations or URLs.
2. Never claim a question was asked in a real interview.
3. Keep the original question text unless it is demonstrably broken; if you change it, say why in `change_notes`.
4. Answers are reference answers an interviewer could grade against: direct answer first, then mechanism/reasoning, then trade-offs, pitfalls or a concrete example where useful. Typical length 60-200 words (coding/SQL answers may be longer). Plain text, no markdown headings. Code goes in fenced blocks (```python / ```sql).
5. `key_concepts`: 3-8 specific, meaningful terms (e.g. "left join", "NULL-safe comparison", "bias-variance trade-off"), each of which is actually discussed in the answer. No generic words ("data", "model", "algorithm"), no duplicates.
6. Executable code: any SQL or Python snippet in an answer must be run by you before you submit. SQL: run with sqlite3 (in-memory); give `setup` (CREATE TABLE/INSERT statements), `solution` (the query shown in the answer) and `expected` (list of result rows as produced). Python: give `test` code (asserts) that imports/executes the solution; run it. Dialect-specific features that SQLite lacks (e.g. FULL OUTER JOIN is fine in 3.45; but not PostgreSQL-only syntax) must not appear in executed examples; mention dialect differences in prose only if you are sure.
7. Sources: list a source only if you actually opened it with WebFetch/WebSearch in this task and confirmed it supports the claim. Each: {"title","url","supports": "<one short sentence of the claim it supports>"}. If you did not open a source, leave `sources` empty -- that is acceptable and honest. Never fabricate.
8. If you cannot make a record confidently correct, set `status` to "defer" and explain in `change_notes`; do not guess.

## Output
Write ONE JSON file (path given in your task): a list of objects:
{
 "id": "smi-0000",
 "status": "ok" | "defer",
 "question": "<final question text>",
 "answer": "<final reference answer>",
 "key_concepts": ["...", ...],            // 3-8
 "difficulty": "Easy"|"Medium"|"Hard",    // by actual complexity: Easy = single-concept recall; Medium = comparison, mechanism, short code or simple application; Hard = multi-step reasoning, design with trade-offs, debugging a subtle problem or non-trivial implementation
 "domain": "Machine Learning"|"Deep Learning"|"NLP"|"Python"|"SQL"|"Data Analysis",
 "code": null | {"language":"sql"|"python","setup":"...","solution":"...","test":"...","expected":[...]},
 "sources": [],
 "change_notes": "what was wrong/weak and what you changed",
 "confidence": "high"|"medium"|"low"
}
Statistics/A-B testing/product-metrics belong to Data Analysis; MLE/Bayes/bias-variance/regularisation etc. stay in Machine Learning.
After writing, print a short summary (counts of ok/defer, any code you executed and the result). Do not modify any file other than your output file.

## Additional rules for NEW (generated) questions (pilot batch)
- Each question must be self-contained: for SQL include the table definitions and the relevant sample data or its shape in the question text; state the exact output required (columns, ordering).
- Each question must be genuinely distinct in intent from every item in /home/claude/work/s1b/existing_questions.json and from each other. Do not use fill-in templates ("Explain X in the context of Y").
- Provenance: these are AI-written original questions. Never say or imply they come from real interviews or a named company's interview.
- Extra output fields: "plan_id" (the id given in your plan), "question_type" ("concept"|"scenario"|"debugging"|"coding"|"sql_exercise"|"design"), "interview_style_note": one line on what a strong candidate demonstrates (used for grading), and "common_mistakes": list of 1-3 typical wrong answers/pitfalls.
- Code answers: provide a complete runnable `solution` and a `test` that asserts behaviour (for SQL: `setup`, `solution`, `expected` rows exactly as sqlite returns them, in the order the query guarantees; if order is not guaranteed by the query, add ORDER BY). Run everything. Numeric expectations must come from executing code, never from memory.
- The answer text must show the same solution code as `solution` inside a fenced block.
- Difficulty: assign by actual complexity; do not try to balance counts.
