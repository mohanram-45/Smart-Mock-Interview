# Concept-scope sidecar `scope_v1`

666 rows, one per question in the frozen corpus (same order and IDs). The corpus, reference answers and previous dataset versions are **not modified**; this file only adds a requirement view on top of them.

**Authorship: AI (Claude). `human_verified` = 0. Nothing here is human-approved.**

| Field | Meaning |
|---|---|
| `question_id`, `question_type`, `domain`, `difficulty` | copied from the corpus (`question_type` empty → `unspecified`) |
| `essential_concepts` | all must be demonstrated for full completeness |
| `essential_groups` | `{label, concepts, min_required}`: at least `min_required` members must be demonstrated; any valid member counts; extras never required |
| `supporting_concepts` | may add credit/feedback; absence never penalised |
| `background_concepts` | feedback only; never penalised or credited |
| `label_concepts` | restate the question topic; satisfied by the essentials |
| `added_concepts` | concepts not in the record's `key_concepts` (derived, e.g. a numeric result) |
| `acceptable_alternative_explanations` | `{text, basis}`; basis ∈ `existing_alternative_answers`, `ai_proposed_technical_equivalent`, `default_policy` |
| `verification_status` | `ai_reviewed_pilot` (77 rows, read by AI) or `ai_heuristic_draft` (589 rows, rule-based) |
| `tier_source` | `manual_pilot`, `manual_zero_essential`, `heuristic_v2` |
| `ambiguity_flags`, `review_notes` | why a human decision is needed |
| `human_review_required` | true if any open ambiguity (400 rows) |
| `completeness_penalty_eligible` | true only for reviewed rows with no open ambiguity (16 rows). Otherwise a missing essential concept may be reported but must not lower the score automatically |

Policy is also stored in `scope_v1_manifest.json` (`penalty_policy`). The manifest holds the sidecar sha256, the frozen-corpus content hash and per-component corpus fingerprints.

Rebuild: `python -m audit.evaluation.build_scope_v1` (byte-identical output). Validate: `python -m audit.evaluation.stage3c_validate`.
