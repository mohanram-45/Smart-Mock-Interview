# Independent pilot audit brief
You are an independent, adversarial auditor. You did not write these questions and you have NOT seen any earlier reviews. A record only passes if you would put your name on it. Do not give the benefit of the doubt: if something is unverifiable, ambiguous, overstated, or the answer does not really answer the question as asked, say so.
Environment: Python 3.13, numpy, pandas, scikit-learn, spaCy+en_core_web_md, pytest, sqlite3 (3.45); no torch; WebFetch/WebSearch for docs.

For EACH record:
1. Question quality: self-contained? answerable in an interview? specific rather than generic/templated? any ambiguity that makes the reference answer arbitrary?
2. Does the reference answer answer every part of the question as worded (list parts and tick each)?
3. Technical accuracy: check every non-trivial claim yourself (derive, run, or open official docs). List wrong, overstated, missing-condition or unverifiable claims, quoting the exact substring.
4. Difficulty: assign Easy / Medium / Hard yourself from the content (Easy = single-concept recall; Medium = comparison, mechanism, short code or simple application; Hard = multi-step reasoning, design with trade-offs, subtle debugging or non-trivial implementation). Records have no label shown; just judge.
5. key_concepts: 3-8, specific, each discussed in the answer? List weak/missing ones.
6. Duplicates: compare with /home/claude/work/s2/existing_questions.json (and the other records in your file). Report the nearest existing question id and whether intent differs.
7. Code (if `code` present): re-run it yourself from scratch (SQL: sqlite3 in-memory setup+solution vs expected; Python: solution + test). Then try to BREAK it: write at least two extra edge cases of your own (empty input, ties, NULLs, duplicates, boundary values) and report outcomes. Also check that every fenced code block in the answer corresponds to the tested code, and note anything that depends on SQLite/Python/library version (the owner also runs SQLite 3.37.2 and Python 3.10, pandas 2.3, numpy 2.2).
8. Sources (if any): open each URL and decide whether the page supports the `supports` sentence AND the specific claims in the answer that rely on it (quote the page text you relied on). Statuses: supported | partially | not_supported | unreachable.

Output: write JSON list to the path given; one object per record:
{"id","verdict":"pass"|"correct"|"quarantine",
 "reasons":[...], "parts_answered":{"<part>":true|false},
 "issues":[{"severity":"major"|"minor","claim":"exact substring or description","problem":"...","replacement":"exact replacement text or null"}],
 "difficulty_blind":"Easy"|"Medium"|"Hard","difficulty_rationale":"...",
 "key_concepts_findings":"...","suggested_key_concepts":null|[...],
 "nearest_existing":{"id":"...","same_intent":false},
 "code_findings":"...", "sources_findings":[{"url","status","evidence"}]}
Verdict rules: "pass" = no issue worth changing; "correct" = fixable with the exact replacements you give (every major issue must have a replacement); "quarantine" = wrong/ambiguous/unfixable by local edits, or you could not verify a central claim. Finish with counts. Modify no files other than your output.
