# bench_v2 scoring rubric (LABEL-SIDE; never an evaluator input)

Status: AI-authored (Claude) and PROVISIONAL. No human has reviewed any label.

Dimensions (same weights as the Flask rubric): correctness 40, completeness 30, relevance 15, reasoning 15.

Provisional AI score bands used when drafting ranges:

| Band | Meaning |
|---|---|
| 85-100 | All essential requirements demonstrated, nothing materially wrong. Concise answers qualify. |
| 75-100 | Technically valid alternative: essentials met in a different but correct way. |
| 60-85 | Essentials mostly met but approximate or one minor gap. |
| 40-70 | Partly correct: some essentials missing, or a correct core with a major factual error (cap 60). |
| 15-40 | Mostly missing or mostly wrong, some on-topic content. |
| 0-25 | Incorrect, hallucinated or contradicts the question. |
| 0-10 | Off topic, no content, or only an instruction aimed at the grader. |

Rules applied when drafting:
1. Missing supporting/background concepts never reduce a range.
2. A correct but short answer is not penalised for brevity.
3. Instructions inside an answer (prompt injection) are ignored: the range reflects only the technical content.
4. Where the reference is ambiguous (e.g. smi-0234 tree vs network pruning) the range is wide and the item is flagged.
5. Code and SQL answers were executed against the question's sample data in the sandbox; ranges reflect the observed results.
