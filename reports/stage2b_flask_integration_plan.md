# Stage 2B — Safe Flask integration plan (design only; nothing in the app was changed)

## Facts found in the app (read from the code, not assumed)
- `InterviewSession.load_questions()` reads `data/processed/questions_cleaned.json` (4,085 rows: `id` int, `domain`, `difficulty`, `question`, `reference_answer`), filters by `selected_domains`, buckets by difficulty and shuffles.
- Question ids are **ints** and are used in `asked_question_ids: Set[int]`, in submit-answer payloads and in `report_generator` (`question_id: int`). The approved corpus ids are **strings** (`smi-0001`, `smi-k0015`, `smi-m0038`).
- The TF-IDF scorer is trained on `[q["reference_answer"] ...]` of the loaded questions (`corpus=`), so changing the question source also changes that scorer's training corpus.
- `/api/domains` is derived from `ROLE_MAPPING` (config), which lists the six legacy domains only.
- `Pretrained_NEURALN.py` loads `SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")` by name (default Hugging Face cache, no `local_files_only`).
- 3,618 of the 4,085 legacy rows are template boilerplate (`data/audit/triage.csv`, `status == EXCLUDE_TEMPLATE`). Measured by `src/retrieval/legacy_guard.py`: the 666 approved records share **0 ids, 0 questions and 0 answers** with those rows.

## Principles
1. Default behaviour unchanged. A flag selects the source; the default stays `legacy`.
2. No scorer changes. Scoring code receives the same four fields it receives today.
3. Retrieval is read-only and additive; it never writes to `data/curated`, `data/expansion` or `data/processed`.
4. Boilerplate can never re-enter through retrieval: enforced by tests, not convention.

## Phased plan (each phase is separately reversible)
| Phase | Change | Gate to proceed |
|---|---|---|
| 0 (now) | Nothing in the app. `legacy_guard.check_disjoint` + tests exist. | Stage 2B decision |
| 1 | Add `QUESTION_SOURCE` env/config (`legacy` default, `approved`). New adapter `approved_questions()` returns legacy-shaped dicts: `id` = stable int (index into the sorted 666-id list, plus `qid` = original `smi-…` string), `domain`, `difficulty`, `question`, `reference_answer = canonical_answer`. Session code keeps using `id`. | Adapter unit tests; id mapping is a pure function of the corpus fingerprint |
| 2 | Add the two new domains to `ROLE_MAPPING` only under `approved`. Check difficulty balance per selected role (an approved-only pool may have too few Hard items for some role/domain mixes). | Per-domain/difficulty counts reviewed |
| 3 | Shadow mode: when `approved`, also log retrieval results for each answered question (no effect on scoring) and compare scorer output on both sources offline. | No regressions in the existing scorer tests |
| 4 | Optional: use retrieval for "related question / follow-up" suggestions. Only after Stage 2B retrieval quality is accepted. | Real MiniLM results (blocked, see report) |

## Guards (all implementable now, most already exist)
- Startup check: `load_corpus(strict=True)` (fingerprint + registry), then `check_disjoint`; abort to `legacy` with a logged error on failure.
- Never index or serve rows with `status == EXCLUDE_TEMPLATE`; assert count 3,618 and disjointness.
- Domain filter uses the corpus domain strings exactly (including `Generative AI & RAG`, `MLOps & Model Deployment`).
- Reference answers are AI-reviewed, not human-verified; the UI/report layer must not present them as verified. `verification.human_reviewed` is `False` for every record and is carried through.
- Candidate answers are never added to the index (already enforced in `documents.py`).

## Not done / open
- Session-id and report storage were not tested with string ids; the int-mapping adapter avoids the question.
- `ROLE_MAPPING` content was not edited. The scorer's TF-IDF corpus changes with the source and needs an offline comparison (Phase 3).
- Windows has not been tested for faiss/torch installs in the project environment.
