# Stage 3C-2.1 full-run analysis (mechanical + AI-provisional; NOT human-validated)

## Run
```
{
 "started_utc": "2026-10-15T12:00:53Z",
 "finished_utc": "2026-10-15T12:54:54Z",
 "total_wall_s": 3165.9,
 "model_load_s": 74.1,
 "ollama_version": "0.32.13",
 "platform": "Windows-11-10.0.26300-SP0",
 "freeze_manifest_sha256": "c54546b6e49bbc1addb105fe81ad9b48312aca163d5b53137e62ce35d13f1d08",
 "partial_run": false
}
```

## Frozen decision

DO NOT ADVANCE: report which criterion failed and why. Do not tune the prompt, gate or rubric on these 20 answers and re-score them; any change requires a new sample.

## Per answer

| id | kind | AI band | modular r0/r1 | legacy (conf) | modular in AI band | legacy in AI band |
|---|---|---|---|---|---|---|
| b2-004 | hallucinated | [0, 15] | 36 / 36 (sco/sco) | 15 (medium) | [False, False] | True |
| b2-005 | partial | [45, 70] | None / None (abs/abs) | 30 (low) | [None, None] | False |
| b2-006 | correct_full | [85, 100] | 100 / 100 (sco/sco) | 75 (medium) | [True, True] | False |
| b2-012 | incorrect | [0, 25] | None / None (abs/abs) | 30 (low) | [None, None] | False |
| b2-013 | valid_alternative | [80, 100] | None / None (abs/abs) | 30 (low) | [None, None] | False |
| b2-015 | injection | [0, 25] | None / None (abs/abs) | 15 (low) | [None, None] | True |
| b2-023 | incorrect | [0, 20] | None / 36 (abs/sco) | 8 (medium) | [None, False] | True |
| b2-026 | correct_full | [85, 100] | 100 / 100 (sco/sco) | 75 (medium) | [True, True] | False |
| b2-028 | hallucinated | [0, 25] | 50 / 50 (sco/sco) | 25 (low) | [False, False] | True |
| b2-043 | partial | [50, 75] | 90 / 80 (sco/sco) | 55 (medium) | [False, False] | True |
| b2-045 | concise_sufficient | [85, 100] | 89 / None (sco/abs) | 96 (medium) | [True, None] | True |
| b2-048 | partial | [60, 85] | None / None (abs/abs) | 54 (medium) | [None, None] | False |
| b2-068 | concise_sufficient | [85, 100] | 89 / 89 (sco/sco) | 75 (medium) | [True, True] | False |
| b2-072 | valid_alternative | [85, 100] | 100 / 100 (sco/sco) | 64 (medium) | [True, True] | False |
| b2-105 | injection_weak | [0, 25] | None / None (abs/abs) | 25 (low) | [None, None] | True |
| b2-109 | valid_alternative | [80, 100] | 80 / 80 (sco/sco) | 30 (low) | [True, True] | False |
| b2-112 | concise_sufficient | [90, 100] | 100 / 100 (sco/sco) | 68 (medium) | [True, True] | False |
| b2-115 | injection_with_correct | [80, 100] | 89 / 89 (sco/sco) | 30 (low) | [True, True] | False |
| s2-f01 | off_topic | [None, None] | None / None (abs/abs) | 0 (medium) | [None, None] | None |
| s2-f02 | non_substantive | [None, None] | None / None (abs/abs) | 29 (medium) | [None, None] | None |

## Modular vs legacy (matched)
```
{
 "answers_both_scored_in_both_repeats": [
  "b2-004",
  "b2-006",
  "b2-026",
  "b2-028",
  "b2-043",
  "b2-068",
  "b2-072",
  "b2-109",
  "b2-112",
  "b2-115"
 ],
 "n": 10,
 "mean_signed_diff_modular_minus_legacy": 31.7,
 "mean_abs_diff": 31.7,
 "modular_higher": 10,
 "legacy_higher": 0,
 "equal": 0,
 "spearman_rank_correlation": 0.831,
 "legacy_graded_all_20": 20,
 "legacy_low_confidence": 11,
 "modular_abstained_in_at_least_one_repeat": [
  "b2-005",
  "b2-012",
  "b2-013",
  "b2-015",
  "b2-023",
  "b2-045",
  "b2-048",
  "b2-105",
  "s2-f01",
  "s2-f02"
 ],
 "legacy_score_on_modular_abstentions": {
  "b2-005": 30,
  "b2-012": 30,
  "b2-013": 30,
  "b2-015": 15,
  "b2-023": 8,
  "b2-045": 96,
  "b2-048": 54,
  "b2-105": 25,
  "s2-f01": 0,
  "s2-f02": 29
 },
 "caveat": "No human score exists; 'higher' is not 'more accurate'."
}
```

## AI-band consistency (NOT accuracy)
```
{
 "label": "AI-authored provisional bands; consistency with them is NOT grading accuracy",
 "modular": {
  "numeric_scores_compared": 22,
  "inside_ai_band": 15,
  "above_band": [
   [
    "b2-004",
    36,
    [
     0,
     15
    ]
   ],
   [
    "b2-004",
    36,
    [
     0,
     15
    ]
   ],
   [
    "b2-023",
    36,
    [
     0,
     20
    ]
   ],
   [
    "b2-028",
    50,
    [
     0,
     25
    ]
   ],
   [
    "b2-028",
    50,
    [
     0,
     25
    ]
   ],
   [
    "b2-043",
    90,
    [
     50,
     75
    ]
   ],
   [
    "b2-043",
    80,
    [
     50,
     75
    ]
   ]
  ],
  "below_band": []
 },
 "legacy": {
  "numeric_scores_compared": 18,
  "inside_ai_band": 7,
  "above_band": [
   [
    "b2-012",
    30,
    [
     0,
     25
    ]
   ]
  ],
  "below_band": [
   [
    "b2-005",
    30,
    [
     45,
     70
    ]
   ],
   [
    "b2-006",
    75,
    [
     85,
     100
    ]
   ],
   [
    "b2-013",
    30,
    [
     80,
     100
    ]
   ],
   [
    "b2-026",
    75,
    [
     85,
     100
    ]
   ],
   [
    "b2-048",
    54,
    [
     60,
     85
    ]
   ],
   [
    "b2-068",
    75,
    [
     85,
     100
    ]
   ],
   [
    "b2-072",
    64,
    [
     85,
     100
    ]
   ],
   [
    "b2-109",
    30,
    [
     80,
     100
    ]
   ],
   [
    "b2-112",
    68,
    [
     90,
     100
    ]
   ],
   [
    "b2-115",
    30,
    [
     80,
     100
    ]
   ]
  ]
 }
}
```

## Abstention causes

```
{
 "primary": {
  "model_uncertain": 5,
  "evidence_gate": 8,
  "mixed_model_and_gate": 3,
  "off_topic_confirmed": 2
 },
 "by_kind": {
  "concise_sufficient": {
   "evidence_gate": 1
  },
  "incorrect": {
   "evidence_gate": 3
  },
  "injection": {
   "evidence_gate": 2
  },
  "injection_weak": {
   "model_uncertain": 1,
   "mixed_model_and_gate": 1
  },
  "non_substantive": {
   "evidence_gate": 2
  },
  "off_topic": {
   "off_topic_confirmed": 2
  },
  "partial": {
   "model_uncertain": 4
  },
  "valid_alternative": {
   "mixed_model_and_gate": 2
  }
 }
}
```

| id | rep | kind | primary | blockers |
|---|---|---|---|---|
| b2-005 | 0 | partial | model_uncertain | E2:model_unverified |
| b2-012 | 0 | incorrect | evidence_gate | E1:gate_downgraded; E2:gate_downgraded |
| b2-013 | 0 | valid_alternative | mixed_model_and_gate | E2:model_unverified; S3:gate_downgraded; S4:gate_downgraded |
| b2-015 | 0 | injection | evidence_gate | E1:gate_downgraded; E2:gate_downgraded |
| b2-023 | 0 | incorrect | evidence_gate | E1:gate_downgraded |
| b2-048 | 0 | partial | model_uncertain | E2:model_unverified |
| b2-105 | 0 | injection_weak | model_uncertain | G1:model_unverified; G1:model_unverified; G1:model_unverified; G1:model_unverified |
| s2-f01 | 0 | off_topic | off_topic_confirmed | E1:gate_downgraded |
| s2-f02 | 0 | non_substantive | evidence_gate | E2:gate_downgraded |
| b2-005 | 1 | partial | model_uncertain | E2:model_unverified |
| b2-012 | 1 | incorrect | evidence_gate | E1:gate_downgraded; E2:gate_downgraded |
| b2-013 | 1 | valid_alternative | mixed_model_and_gate | E2:model_unverified; S3:gate_downgraded; S4:gate_downgraded |
| b2-015 | 1 | injection | evidence_gate | E1:gate_downgraded; E2:gate_downgraded |
| b2-045 | 1 | concise_sufficient | evidence_gate | E1:gate_downgraded; E2:gate_downgraded |
| b2-048 | 1 | partial | model_uncertain | E2:model_unverified |
| b2-105 | 1 | injection_weak | mixed_model_and_gate | G1:model_unverified; G1:model_unverified; G1:model_unverified; G1:model_unverified; G1:gate_downgraded |
| s2-f01 | 1 | off_topic | off_topic_confirmed | E1:gate_downgraded |
| s2-f02 | 1 | non_substantive | evidence_gate | E2:gate_downgraded |

## Grounding
```
{
 "claim_or_evidence_span_mismatches": [],
 "reference_quotes_total": 20,
 "reference_quotes_found_in_reference": 20,
 "reference_quotes_not_found": [],
 "positive_credit_verdicts": 72,
 "positive_credit_with_zero_member_stem_support": [
  {
   "sample_id": "b2-005",
   "repeat": 0,
   "req": "E1",
   "member": "sinusoidal positional encoding",
   "share": 0.0,
   "claim": "```python\nimport numpy as np\ndef sinusoidal_pe(n_pos, d_model):\n    pos = np.arange(n_pos)[:, None]\n    freq = 1.0 / 100"
  },
  {
   "sample_id": "b2-013",
   "repeat": 0,
   "req": "E1",
   "member": "sinusoidal positional encoding",
   "share": 0.0,
   "claim": "```python\nimport math\ndef sinusoidal_pe(n_pos, d_model):\n    pe = [[0.0] * d_model for _ in range(n_pos)]\n    for p in r"
  },
  {
   "sample_id": "b2-026",
   "repeat": 0,
   "req": "E1",
   "member": "silent failure",
   "share": 0.0,
   "claim": "An ML result depends on more than the code, and the extra dependencies fail silently: a wrong version in ordinary softwa"
  },
  {
   "sample_id": "b2-026",
   "repeat": 0,
   "req": "G1",
   "member": "container image",
   "share": 0.0,
   "claim": "Sources: data (a sample or older extract versus the refreshed table), unpinned dependencies that change defaults, hardwa"
  },
  {
   "sample_id": "b2-028",
   "repeat": 0,
   "req": "S1",
   "member": "feedforward neural network",
   "share": 0.0,
   "claim": "CNNs were invented by Geoffrey Hinton in 2012 and use max-pooling as their only layer type."
  },
  {
   "sample_id": "b2-043",
   "repeat": 0,
   "req": "E2",
   "member": "shortest path",
   "share": 0.0,
   "claim": "```python\nimport heapq\ndef dijkstra(graph, source):\n    dist = {u: float(\"inf\") for u in graph}\n    dist[source] = 0\n   "
  },
  {
   "sample_id": "b2-043",
   "repeat": 0,
   "req": "S1",
   "member": "min-heap",
   "share": 0.0,
   "claim": "```python\nimport heapq\ndef dijkstra(graph, source):\n    dist = {u: float(\"inf\") for u in graph}\n    dist[source] = 0\n   "
  },
  {
   "sample_id": "b2-048",
   "repeat": 0,
   "req": "S1",
   "member": "normal distribution",
   "share": 0.0,
   "claim": "The data left are the two tails outside one standard deviation."
  },
  {
   "sample_id": "b2-048",
   "repeat": 0,
   "req": "S3",
   "member": "symmetry of the normal",
   "share": 0.0,
   "claim": "The data left are the two tails outside one standard deviation."
  },
  {
   "sample_id": "b2-072",
   "repeat": 0,
   "req": "E1",
   "member": "68-95-99.7 rule",
   "share": 0.0,
   "claim": "The remaining fraction is 0.317 (about 32%): the two tails with |z| > 1, each about 0.1587."
  },
  {
   "sample_id": "b2-072",
   "repeat": 0,
   "req": "S1",
   "member": "normal distribution",
   "share": 0.0,
   "claim": "The remaining fraction is 0.317 (about 32%): the two tails with |z| > 1, each about 0.1587."
  },
  {
   "sample_id": "b2-072",
   "repeat": 0,
   "req": "S3",
   "member": "symmetry of the normal",
   "share": 0.0,
   "claim": "The remaining fraction is 0.317 (about 32%): the two tails with |z| > 1, each about 0.1587."
  }
 ],
 "positive_credit_with_partial_support_lt_half": [
  {
   "sample_id": "b2-013",
   "repeat": 0,
   "req": "S1",
   "member": "relative offset as rotation",
   "share": 0.33,
   "claim": "For a fixed k, each (sin, cos) pair at angle a maps to angle a + k*w by a 2x2 rotation that does not depend on p, so one"
  },
  {
   "sample_id": "b2-013",
   "repeat": 1,
   "req": "S1",
   "member": "relative offset as rotation",
   "share": 0.33,
   "claim": "For a fixed k, each (sin, cos) pair at angle a maps to angle a + k*w by a 2x2 rotation that does not depend on p, so one"
  }
 ],
 "negative_verdicts": 17,
 "negative_with_zero_overlap_to_member_or_quote": [
  {
   "sample_id": "b2-105",
   "repeat": 0,
   "req": "G1",
   "member": "unpinned dependencies",
   "tier": "essential",
   "share": 0.0,
   "claim": "It is because machine learning needs a GPU that other people may not have.",
   "explanation": "It mentions an incorrect cause."
  },
  {
   "sample_id": "b2-109",
   "repeat": 0,
   "req": "S1",
   "member": "min-heap",
   "tier": "supporting",
   "share": 0.0,
   "claim": "This version needs no heap and runs in O(V^2), which suits dense graphs; weights must be non-negative.",
   "explanation": "This version uses a simple min function, not a heap."
  },
  {
   "sample_id": "b2-105",
   "repeat": 1,
   "req": "G1",
   "member": "unpinned dependencies",
   "tier": "essential",
   "share": 0.0,
   "claim": "It is because machine learning needs a GPU that other people may not have.",
   "explanation": "claims about GPU, not unpinned dependencies"
  },
  {
   "sample_id": "b2-109",
   "repeat": 1,
   "req": "S1",
   "member": "min-heap",
   "tier": "supporting",
   "share": 0.0,
   "claim": "This version needs no heap and runs in O(V^2), which suits dense graphs; weights must be non-negative.",
   "explanation": "This version uses a list to find the minimum distance node, not a heap."
  }
 ]
}
```

## On-topic flag
```
{
 "rows": 40,
 "model_said_off_topic_for_answers_not_labelled_off_topic": [
  {
   "sample_id": "b2-004",
   "repeat": 0,
   "kind": "hallucinated",
   "model_on_topic": "off_topic",
   "lexical_overlap": 0.333,
   "relevance_level": 3
  },
  {
   "sample_id": "b2-015",
   "repeat": 0,
   "kind": "injection",
   "model_on_topic": "off_topic",
   "lexical_overlap": 0.75,
   "relevance_level": null
  },
  {
   "sample_id": "b2-023",
   "repeat": 0,
   "kind": "incorrect",
   "model_on_topic": "off_topic",
   "lexical_overlap": 0.333,
   "relevance_level": null
  },
  {
   "sample_id": "b2-015",
   "repeat": 1,
   "kind": "injection",
   "model_on_topic": "off_topic",
   "lexical_overlap": 0.75,
   "relevance_level": null
  },
  {
   "sample_id": "b2-023",
   "repeat": 1,
   "kind": "incorrect",
   "model_on_topic": "off_topic",
   "lexical_overlap": 0.333,
   "relevance_level": 3
  }
 ],
 "true_off_topic_rows_flagged": [
  {
   "sample_id": "s2-f01",
   "repeat": 0,
   "kind": "off_topic",
   "model_on_topic": "off_topic",
   "lexical_overlap": 0.0,
   "relevance_level": 0
  },
  {
   "sample_id": "s2-f01",
   "repeat": 1,
   "kind": "off_topic",
   "model_on_topic": "off_topic",
   "lexical_overlap": 0.0,
   "relevance_level": 0
  }
 ]
}
```

## Reasoning dimension
```
{
 "expected_but_level_le_1": [
  {
   "sample_id": "b2-012",
   "repeat": 0,
   "level": 1,
   "expected": true,
   "derivation": "0 verified reasoning claim(s); 1 needed for full level"
  },
  {
   "sample_id": "b2-045",
   "repeat": 0,
   "level": 1,
   "expected": true,
   "derivation": "0 verified reasoning claim(s); 1 needed for full level"
  },
  {
   "sample_id": "b2-068",
   "repeat": 0,
   "level": 1,
   "expected": true,
   "derivation": "0 verified reasoning claim(s); 1 needed for full level"
  },
  {
   "sample_id": "b2-105",
   "repeat": 0,
   "level": 1,
   "expected": true,
   "derivation": "0 verified reasoning claim(s); 1 needed for full level"
  },
  {
   "sample_id": "b2-115",
   "repeat": 0,
   "level": 1,
   "expected": true,
   "derivation": "0 verified reasoning claim(s); 1 needed for full level"
  },
  {
   "sample_id": "s2-f02",
   "repeat": 0,
   "level": 1,
   "expected": true,
   "derivation": "0 verified reasoning claim(s); 1 needed for full level"
  },
  {
   "sample_id": "b2-012",
   "repeat": 1,
   "level": 1,
   "expected": true,
   "derivation": "0 verified reasoning claim(s); 1 needed for full level"
  },
  {
   "sample_id": "b2-015",
   "repeat": 1,
   "level": 1,
   "expected": true,
   "derivation": "0 verified reasoning claim(s); 1 needed for full level"
  },
  {
   "sample_id": "b2-045",
   "repeat": 1,
   "level": 1,
   "expected": true,
   "derivation": "0 verified reasoning claim(s); 1 needed for full level"
  },
  {
   "sample_id": "b2-068",
   "repeat": 1,
   "level": 1,
   "expected": true,
   "derivation": "0 verified reasoning claim(s); 1 needed for full level"
  },
  {
   "sample_id": "b2-105",
   "repeat": 1,
   "level": 1,
   "expected": true,
   "derivation": "0 verified reasoning claim(s); 1 needed for full level"
  },
  {
   "sample_id": "b2-115",
   "repeat": 1,
   "level": 1,
   "expected": true,
   "derivation": "0 verified reasoning claim(s); 1 needed for full level"
  },
  {
   "sample_id": "s2-f02",
   "repeat": 1,
   "level": 1,
   "expected": true,
   "derivation": "0 verified reasoning claim(s); 1 needed for full level"
  }
 ],
 "full_marks_by_convention": 24
}
```

## Repeat disagreements
```
{
 "members_compared": 83,
 "agreement_after_gate": 0.9157,
 "agreement_before_gate": 0.9398,
 "mismatches": [
  {
   "sample_id": "b2-023",
   "requirement": "E1",
   "tier": "essential",
   "member": "O(log n)",
   "model": [
    "states_incorrectly",
    "states_incorrectly"
   ],
   "final": [
    "unverified",
    "states_incorrectly"
   ],
   "cause": "gate_induced",
   "gate_reasons": [
    "no_valid_evidence",
    null
   ],
   "status_effect": [
    "abstained",
    "scored"
   ],
   "score_effect": [
    null,
    36
   ]
  },
  {
   "sample_id": "b2-043",
   "requirement": "S3",
   "tier": "supporting",
   "member": "Bellman-Ford",
   "model": [
    "states_correctly",
    "states_incorrectly"
   ],
   "final": [
    "unverified",
    "states_incorrectly"
   ],
   "cause": "model_flip_and_gate",
   "gate_reasons": [
    "no_valid_evidence",
    null
   ],
   "status_effect": [
    "scored",
    "scored"
   ],
   "score_effect": [
    90,
    80
   ]
  },
  {
   "sample_id": "b2-045",
   "requirement": "E1",
   "tier": "essential",
   "member": "Type I error",
   "model": [
    "states_correctly",
    "states_correctly"
   ],
   "final": [
    "states_correctly",
    "unverified"
   ],
   "cause": "gate_induced",
   "gate_reasons": [
    null,
    "same_claim_correct_and_incorrect"
   ],
   "status_effect": [
    "scored",
    "abstained"
   ],
   "score_effect": [
    89,
    null
   ]
  },
  {
   "sample_id": "b2-045",
   "requirement": "E2",
   "tier": "essential",
   "member": "Type II error",
   "model": [
    "states_correctly",
    "states_incorrectly"
   ],
   "final": [
    "states_correctly",
    "unverified"
   ],
   "cause": "model_flip_and_gate",
   "gate_reasons": [
    null,
    "same_claim_correct_and_incorrect"
   ],
   "status_effect": [
    "scored",
    "abstained"
   ],
   "score_effect": [
    89,
    null
   ]
  },
  {
   "sample_id": "b2-045",
   "requirement": "S2",
   "tier": "supporting",
   "member": "false negative",
   "model": [
    "states_correctly",
    "states_incorrectly"
   ],
   "final": [
    "states_correctly",
    "states_incorrectly"
   ],
   "cause": "model_flip",
   "gate_reasons": [
    null,
    null
   ],
   "status_effect": [
    "scored",
    "abstained"
   ],
   "score_effect": [
    89,
    null
   ]
  },
  {
   "sample_id": "b2-072",
   "requirement": "S3",
   "tier": "supporting",
   "member": "symmetry of the normal",
   "model": [
    "states_correctly",
    "unverified"
   ],
   "final": [
    "states_correctly",
    "unverified"
   ],
   "cause": "model_flip",
   "gate_reasons": [
    null,
    null
   ],
   "status_effect": [
    "scored",
    "scored"
   ],
   "score_effect": [
    100,
    100
   ]
  },
  {
   "sample_id": "b2-105",
   "requirement": "G1",
   "tier": "essential",
   "member": "__other_valid__",
   "model": [
    "not_stated",
    "states_correctly"
   ],
   "final": [
    "not_stated",
    "unverified"
   ],
   "cause": "model_flip_and_gate",
   "gate_reasons": [
    null,
    "no_valid_evidence"
   ],
   "status_effect": [
    "abstained",
    "abstained"
   ],
   "score_effect": [
    null,
    null
   ]
  }
 ],
 "by_cause": {
  "gate_induced": 2,
  "model_flip_and_gate": 3,
  "model_flip": 2
 },
 "mismatch_on_essential": 4
}
```
