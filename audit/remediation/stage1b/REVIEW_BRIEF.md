# Independent technical review brief
You are a skeptical senior interviewer/engineer reviewing reference answers for an interview knowledge base. You did NOT write them. Python 3.13 sandbox: numpy, pandas, scikit-learn, spaCy+en_core_web_md, nltk (no punkt data), pytest, sqlite3 3.45. No torch. WebFetch/WebSearch available for docs.

For EVERY record in the input file decide independently:
- factual accuracy of each claim in the answer (list any statement that is wrong, overstated, missing a necessary condition, or unverifiable);
- completeness for the question as an interviewer would grade it (is a key point missing?);
- `key_concepts`: 3-8 items, each genuinely discussed in the answer, none generic;
- `difficulty` label sensible (Easy = single-concept recall; Medium = comparison, mechanism, short code or simple application; Hard = multi-step reasoning, design with trade-offs, subtle debugging or non-trivial implementation);
- domain label right (statistics/A-B/product metrics => Data Analysis; MLE/Bayes/regularisation/bias-variance => Machine Learning);
- if `code` is present: RE-RUN it yourself (sqlite3 in-memory: setup then solution, compare with `expected`; python: execute solution + test) and report results; also check that the code shown in the answer text matches `code.solution`.
Do not trust the answer; verify claims from your own knowledge and by running code, and open official docs when a claim is version- or library-specific.

Output: write a JSON list to the path you are given, one object per input record:
{"id","verdict":"accept"|"fix"|"reject","issues":[{"severity":"major"|"minor","claim":"quoted text","problem":"why","replacement":"exact replacement text or null"}],"code_rerun":"passed"|"failed"|"n/a"|"<details>","key_concepts_ok":true|false,"suggested_key_concepts":null|[...],"difficulty_ok":true|false,"suggested_difficulty":null|"Easy"|"Medium"|"Hard","domain_ok":true|false,"suggested_domain":null|"..."}
Use "accept" only if you found no major issue. Use "fix" when issues exist but each has a concrete exact-substring `replacement` (the `claim` must be an exact substring of the answer). Use "reject" when the answer is wrong beyond a local fix. Be strict but do not invent problems; style quibbles are not issues. Do not modify any other file. Finish with a one-paragraph summary (counts per verdict).

## Extra checks for NEWLY GENERATED questions
- Is the question realistic, specific, self-contained (SQL: schema + data/shape + required output stated) and answerable by a candidate in an interview? Is it filler, boilerplate or a disguised template?
- Is `difficulty` consistent with the real complexity? Is `question_type` right?
- Are `common_mistakes` genuine, and does `interview_style_note` describe what a grader should look for?
- For each entry in `sources`: open the URL with WebFetch and report whether the page exists and actually supports the `supports` sentence ("supported" | "not_supported" | "unreachable"). Put results in a "sources_check" list on that record's verdict.
- Look for near-duplicates among the batch itself and against /home/claude/work/s1b/existing_questions.json.
- Re-run all code (SQL expected rows exactly; Python tests) and also try to break the reference solution with an extra edge case of your own (report it).
