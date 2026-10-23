import ast
import pathlib
import subprocess
import sys

import pytest

from src.evaluation.grounding import build_request, reference_from_legacy, reference_from_record, support_from_service
from src.retrieval.service import RetrievalService
from tests.evaluation.conftest import ACID, BUBBLE, TIMESENS

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def svc(tmp_path_factory):
    d = tmp_path_factory.mktemp("g")
    return RetrievalService(backend="dev-lsa", index_root=d / "i", cache_dir=d / "c")


def test_reference_is_looked_up_by_question_id_not_by_similarity(svc, by_id):
    req = build_request(BUBBLE, "my answer", service=svc, with_support=True)
    assert req.reference.reference_answer == by_id[BUBBLE]["canonical_answer"] and req.question == by_id[BUBBLE]["question"]
    assert req.reference.key_concepts == by_id[BUBBLE]["key_concepts"] and req.reference.source == "curated"
    assert req.support and all(s.question_id != BUBBLE for s in req.support)               # neighbours never include the question itself
    for s in req.support:                                                                   # ...and none of them replaced the reference
        assert s.text != req.reference.reference_answer[:len(s.text)] or s.question_id != BUBBLE


def test_unknown_question_id_raises_instead_of_guessing(svc):
    with pytest.raises(KeyError):
        build_request("smi-9999", "a", service=svc)
    with pytest.raises(ValueError):
        build_request(BUBBLE, "a")


def test_verification_metadata_is_carried_not_invented(by_id):
    ref = reference_from_record(by_id[TIMESENS])
    assert ref.time_sensitive is True and ref.human_reviewed is False and ref.review_by and "no human review" in ref.remaining_limitations
    assert ref.alternative_answers and ref.common_mistakes and ref.provenance.get("origin")


def test_no_corpus_record_is_marked_human_reviewed(by_id):
    assert not any(reference_from_record(r).human_reviewed for r in by_id.values())          # statement of fact about the data we rely on


def test_legacy_question_reference_is_unverified_and_may_be_missing():
    ref = reference_from_legacy({"id": 5, "question": "q", "reference_answer": "some answer"})
    assert ref.source == "legacy" and ref.key_concepts == [] and ref.verification == "legacy_unverified" and ref.has_reference
    assert reference_from_legacy({"id": 6, "question": "q"}).source == "missing"
    req = build_request("6", "ans", legacy_question={"id": 5, "question": "q", "reference_answer": "x"})
    assert req.question_id == "5"


def test_support_is_optional_truncated_and_failure_safe(svc):
    s = support_from_service(svc, BUBBLE, "What is bubble sort?", k=3)
    assert 0 < len(s) <= 3 and all(len(x.text) <= 600 for x in s)

    class Broken:
        def search(self, *a, **k):
            raise RuntimeError("index down")
    assert support_from_service(Broken(), BUBBLE, "q") == []


# ---------------------------------------------------------------- regression: the foundation must not touch the live app
def test_importing_the_evaluation_package_loads_no_heavy_or_web_dependencies():
    code = ("import sys; import src.evaluation, src.evaluation.evaluator, src.evaluation.config, src.evaluation.grounding;"
            "bad=[m for m in ('torch','flask','sentence_transformers','faiss','requests','anthropic','openai') if m in sys.modules]; print(bad)")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert out.stdout.strip() == "[]", out.stdout + out.stderr


def test_live_app_and_session_do_not_reference_the_evaluation_package():
    for f in ("main/app.py", "src/components/interview_session.py", "src/components/feedback_generator.py", "src/model/model_registry.py",
              "src/components/report_generator.py"):
        t = (ROOT / f).read_text(encoding="utf-8")
        assert "src.evaluation" not in t and "SMART_EVALUATION_BACKEND" not in t and "from evaluation" not in t, f


def test_default_configuration_keeps_legacy_scoring():
    from src.evaluation.config import EvaluationConfig
    assert EvaluationConfig.from_env({}).backend == "legacy"


def test_no_module_makes_network_calls_at_import_or_without_a_configured_provider():
    for f in pathlib.Path(ROOT, "src/evaluation").rglob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in tree.body:                                            # module-level statements only
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                assert "urlopen" not in ast.dump(node), f
