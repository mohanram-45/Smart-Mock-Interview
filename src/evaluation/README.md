# src/evaluation - Stage 3A LLM evaluation foundation

**Status: offline foundation. Not wired into Flask. No provider configured by default. No real LLM has been called.**
Default `SMART_EVALUATION_BACKEND=legacy` (the existing Bi-LSTM / Sentence-BERT / TF-IDF scoring is untouched).

```
EvaluationRequest  (question id/text/domain/topic/difficulty, candidate answer,
  │                 ReferenceBundle looked up BY ID, optional SupportSnippets from FAISS)
  ▼
AnswerEvaluator.evaluate()
  1 pre-checks: empty / non-answer -> not_gradable ; no reference + no key concepts -> insufficient_evidence (model NOT called)
  2 prompt.build_prompt: trusted task + fallible reference + nonce-fenced UNTRUSTED candidate/support
  3 provider.generate (timeouts, bounded retries for transient errors only, clear ProviderError codes)
  4 strict JSON -> LLMEvaluation (pydantic) ; one repair re-ask ; else invalid_response
  5 verify quotes, drop unverifiable, deterministic score from rubric levels + caps, confidence/status from grounding facts
  ▼
EvaluationResult (never fabricated on failure; human_validated is always False)
```

| file | role |
|---|---|
| `schema.py` | Pydantic models: request, `LLMEvaluation` (model contract), `EvaluationResult` |
| `rubric.py`, `RUBRIC.md` | weights, levels, caps, bands |
| `grounding.py` | reference by question ID (curated or legacy), optional retrieved support (self excluded) |
| `prompt.py` | system prompt + fenced user prompt (`PROMPT_VERSION`) |
| `injection.py` | heuristic flagging only |
| `evaluator.py` | the pipeline above |
| `providers/` | `LLMProvider` ABC, `MockProvider` (tests), `http.py` (Ollama, Anthropic, OpenAI-compatible; stdlib only) |
| `config.py` | env configuration and provider factory |

## Environment variables (all optional)
`SMART_EVALUATION_BACKEND=legacy|llm` (default legacy) · `SMART_LLM_PROVIDER=none|ollama|anthropic|openai_compatible` (default none) ·
`SMART_LLM_MODEL` (required, no default) · `SMART_LLM_BASE_URL` · `SMART_LLM_API_KEY` (or `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`) ·
`SMART_LLM_ALLOW_PAID=1` (required for hosted providers) · `SMART_LLM_TIMEOUT_S` (1-300, default 60) · `SMART_LLM_MAX_RETRIES` (0-5, default 2).

## Use (offline)
```
python scripts/stage3a_show_prompt.py --qid smi-0453 --answer "..."       # prints the exact prompt; calls nothing
python -m pytest tests/evaluation -q                                       # needs pydantic (requirements-llm.txt)
```
Mock-provider tests prove the *contracts*; they say nothing about real LLM grading accuracy.
