# Stage 2A independent retrieval evaluation set (v1.1)

| File | Content |
|---|---|
| `eval_set.jsonl` | 166 queries. `relevant` = consensus grades (min of two blind passes); `judged` = every record a labeller saw for that query. 20 queries have no relevant record (out-of-corpus). |
| `eval_set_union_labels.jsonl` | Same queries, grade = max of the two passes (sensitivity check). |
| `*_v1.0*` | The sets before gap labelling (frozen copies for audit). |
| `eval_set_report.json` | Labeller agreement and composition at v1.0. |

How it was built (all steps AI-performed; no human judged any label):
1. Targets were sampled with a fixed seed (`audit/retrieval/sample_briefs.py`).
2. Query authors saw only target topic + key concepts (never question/answer text) and wrote 144 queries in 5 categories; a separate author wrote 22 out-of-corpus queries.
3. The candidate pool per query = union of the top 10 of four rankers (BM25 and a dev LSA embedder, two document modes each) plus the authors' targets.
4. Two independent blind labelling passes (anonymised candidates, different order) judged every pooled candidate on a 0/1/2 scale without seeing the author's target, ranker, rank or score. Agreement: raw 94.5%, Cohen's kappa 0.81 (3-class) / 0.86 (grade>=2).
5. v1.1 adds gap labelling (667 query-record pairs retrieved by the benchmarked systems but not in the pool; same two-pass procedure, raw agreement 98.7%).

Limits: labellers and authors are AI models of one family (correlated errors are possible), pools are built from lexical and LSA rankers (a different retriever, e.g. MiniLM, can surface records nobody judged: use `audit/retrieval/gap_label.py` after each new benchmark and watch `unjudged@10`), 166 queries give wide confidence intervals, and records inside one topic often overlap so "relevant" is partly a judgement call.


## v2 pooled judgements (Stage 2B)
`eval_set_v2.jsonl` = v1.1 + 1,535 newly judged (query, record) pairs that BM25 / MiniLM / hybrid (q, qk, qka) returned in their top 10 but v1.1 had not judged. Two blind passes, a third blind pass on 54 disputed pairs, final = median. `eval_set_v2_min.jsonl` (min of passes 1–2) and `eval_set_v2_max.jsonl` (max) are sensitivity variants. `immutable_pre_pooling_stage2b/` holds the untouched v1.1 files and the Windows benchmark with SHA-256 sums. Judgements are AI-generated, not human ground truth. See `pooling_report_v2.json`.
