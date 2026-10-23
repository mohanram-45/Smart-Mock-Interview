# Consolidated verification backlog (Stage 1D, staged batches 1-4)

282 open items. Full list: `reports/verification_backlog.csv` (columns: backlog_id, batch, record_id, plan_id, category, item, status, suggested_action, priority). Nothing here changes any staged record; the batches are preserved as approved.

## Counts by batch and category

| batch    |   global |   known_minor_gap |   no_external_source |   partial_source |   time_sensitive |   unexecuted_config |   unsupported_claim |
|:---------|---------:|------------------:|---------------------:|-----------------:|-----------------:|--------------------:|--------------------:|
| all      |        1 |                 0 |                    0 |                0 |                0 |                   0 |                   0 |
| batch_01 |        0 |                 0 |                    6 |               24 |                1 |                   0 |                  67 |
| batch_02 |        0 |                 0 |                   17 |                4 |                8 |                   0 |                  54 |
| batch_03 |        0 |                 2 |                    5 |                6 |                6 |                   5 |                  37 |
| batch_04 |        0 |                 7 |                    3 |                7 |                2 |                   0 |                  20 |

## By priority

| priority   |   count |
|:-----------|--------:|
| low        |     227 |
| medium     |      54 |
| high       |       1 |

## By triage (checkpoint, 2026-10-11)

| triage                         |   high |   low |   medium |
|:-------------------------------|-------:|------:|---------:|
| documentation_note             |      0 |     9 |        0 |
| evidence_gap_hedged_or_derived |      0 |   177 |       32 |
| evidence_gap_not_executed      |      0 |     0 |        5 |
| evidence_gap_partial_source    |      0 |    41 |        0 |
| human_review_limitation        |      1 |     0 |        0 |
| scheduled_reverification       |      0 |     0 |       17 |

Checkpoint triage result: **0 medium items are confirmed correctness defects.** All medium unsupported claims are hedged, illustrative or derived reasoning; time-sensitive items are scheduled re-verification; the 5 Batch 3 configs are unexecuted (4 YAML fragments schema-valid when wrapped in a Deployment, never applied; 1 Dockerfile syntax-parsed only, never built). Two checkable claims were re-examined: object stores lacking atomic directory rename (consistent with search results and the Hadoop S3 committer rationale, which cites lack of an efficient rename; the record is hedged) and HPA scale-down stabilisation (could not be read from the K8s page in full; record keeps it as standard practice). Neither was changed.

## Categories

* **unsupported_claim**: statements that rest on background knowledge only (from each batch's `unverified_claims.csv`); includes operational claims such as Batch 3's autoscaler scale-down advice, circuit-breaker claim and TTL sentence.
* **unexecuted_config**: YAML/Dockerfile snippets that were parsed (and Kubernetes objects schema-checked when complete) but never built or applied. Batch 3's five snippets are YAML fragments and one Dockerfile: syntax only, no schema check, no build.
* **partial_source**: citations that support only a narrower statement than the topic.
* **time_sensitive**: records to re-verify by their `review_by` date.
* **no_external_source**: no citation and no executed test.
* **known_minor_gap**: non-blocking observations from final auditors.
* **global**: no human review.