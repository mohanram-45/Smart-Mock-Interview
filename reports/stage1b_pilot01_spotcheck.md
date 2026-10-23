# Stage 1B - independent spot-check of pilot batch 01

Machine-readable evidence: `data/curated/v3/pilot01_spotcheck.json` / `.csv` (every issue, replacement, rating, code and source finding) and `pilot01_corrections.csv` (every field that changed between v2 and v3).

## Method

* **Stratified sample of 21 of the 41** (you asked for >= 15): NLP 7, Deep Learning 5, SQL 9; Medium 12, Hard 9. All 9 Hard pilot questions are in the sample. Sampled ids: g0001 g0003 g0005 g0006 g0008 g0010 g0012 (NLP), g0016 g0020 g0021 g0023 g0026 (DL), g0027 g0029 g0030 g0031 g0034 g0036 g0038 g0040 g0041 (SQL).
* **Extended to the other 20.** My rule was: if about 20 % or more of the sample needed content-level corrections, audit the rest. 5 of 21 did (g0010, g0012, g0023, g0026, g0040), so the remaining 14 NLP/DL and 6 SQL questions were audited the same way. All 41 are now audited.
* **Auditors** were separate agents that did not write the questions and had not seen the earlier reviews. Each one rated difficulty blind, listed which parts of the question the answer covers, checked every non-trivial claim, re-ran all code and tried to break it with its own edge cases, searched for near-duplicates among 401 existing questions, and opened every cited source.
* **My own checks:** I re-ran every code test on real Python 3.10.20, 3.11.17 (numpy 2.2.6, pandas 2.3.3) and 3.13.16 (numpy 2.5.3, pandas 3.0.5), and I opened all 11 cited pages myself.

## Result

| | Sample (21) | Remaining (20) | All 41 |
|---|---:|---:|---:|
| Pass, no change needed | 13 | 8 | 21 |
| Correct (fixable by exact replacement) | 8 | 12 | 20 |
| Quarantine | 0 | 0 | **0** |
| Records with a major issue | 2 | 5 | 7 |
| Major issues / minor issues | 4 / 23 | 5 / 19 | 9 / 42 |

Nothing was passed "by default": 20 of 41 got a "correct" verdict, 25 of 41 records changed in some field (39 replacements applied, including minor ones on records the auditor passed; minor remarks that had no replacement are kept in `review_notes`). Roughly 1 in 6 questions had a major defect that only an independent read caught.

## Findings by check

**Technical accuracy - real errors found and fixed**
* g0039: answer said a month-skipping `LAG` reports "+50 %" for April; it is -50.0 % (3 vs 6 orders), and the correct value is NULL.
* g0018: claimed batch norm "has no meaningful statistic" at batch size 1 in decoding, contradicting the answer's own point that inference uses running averages.
* g0035: answer narrated the author's process ("I put...", "returned 100") and the value 100 does not come from the question's data (with all salaries equal, the compact form returns that salary on SQLite 3.37.2 and NULL on 3.45.1 - re-confirmed by the auditor on a real 3.37.2 build).
* g0007: "fast on CPU, works well with a few thousand labels" stated without conditions although the 50 ms budget is the whole point.
* g0022: original ResNet applies ReLU after the addition; authors say vanishing gradients are unlikely to be the cause of degradation.
* g0017: "whatever the gradient scale" needs the condition gradient >> eps. g0019: sampling-error argument conflated with epoch-to-epoch swings.

**Answer really addresses the question**
* g0010 gave no trade-offs for chunking, hybrid retrieval and index freshness although the question asks for them (3 majors, fixed with explicit trade-off text).
* g0012's test needed `nltk`, which your machine does not have; the NLTK cross-check was removed from the test and the answer.
* g0014 ("demonstrate the root cause in code") only defined the vectorizers; the demonstration was in a hidden test. Fixed by adding the demonstration to the answer and to the executed test.
* 9 answers pointed to tests or runs the reader never sees (g0002, g0014, g0015, g0017, g0020, g0024, g0025, g0040, g0041); wording corrected or the check shown.

**Difficulty** (blind rating vs label): 4 of 41 disagreed. Adopted: g0023 Hard -> Medium, g0038 Hard -> Medium, g0011 Medium -> Hard, g0039 Medium -> Hard. Kept: g0029 stays Medium (auditor said Hard; one frame-semantics subtlety on top of a short query) - recorded in `review_notes`.

**Key concepts:** g0031 had "correlated subquery" the answer never explains (list replaced by the auditor's); g0005 listed "cross-entropy", which the answer never uses (dropped).

**Duplicates:** none. The nearest existing question for every record has a different intent (all listed in the JSON).

**Code:** all 28 tests re-run by the auditors; SQL also on a real SQLite 3.37.2 (identical to 3.45.1 except the g0035 anomaly already fixed in v2). Five records had their recorded code/test changed after audit: g0012 (nltk removed), g0014, g0017, g0025 (demonstration added to the executed test) and g0021 (dtype preserved, validate `p` first); all five re-passed on 3.10, 3.11 and 3.13. g0002 and g0014 test scikit-learn behaviour, so they are skipped on a machine without scikit-learn; everything else runs on stdlib + numpy + pandas.

**Sources (14 citations on 12 records, 11 distinct pages):** the auditors marked 12 supported and 2 partially (g0002 and g0014 cite the scikit-learn feature-extraction page for the CountVectorizer defaults and the "known issues" of the english stop list; the page says "at least 2 letters" without the regex and does not say that negators such as "not" are in the list - those two facts were verified by running the code). I opened all 11 pages myself (Hugging Face tokenizer summary; Transformer paper PDF; word2vec negative-sampling paper PDF; scikit-learn TfidfTransformer, feature extraction and LDA pages; sqlite.org window functions, WITH, foreign keys, optimizer overview, expression indexes) and agree with those statuses. The `verification` field of g0002's second source and g0014's source now says `independent_reviewer_partially`. Precision notes that do not change the records: the SQLite window page never literally says "use an outer query" (it follows from the placement rule); expression-index matching is "exactly as written, except white-space"; the determinism rule applies to function calls in the index expression; LDA perplexity is documented as "approximate perplexity" (the bound wording is on `score`).

## Limits

* All auditors are AI agents; no human subject-matter expert has reviewed any record.
* The corrections come from the auditors' replacement text, applied by script. They were not re-audited by a third reviewer; changed code was re-executed (cross-version results in `cross_version_results.json`).
* The same family of model wrote and audited the questions, so shared blind spots are possible. Please spot-check a few of the 20 corrected records yourself (the `pilot01_corrections.csv` file lists them).
