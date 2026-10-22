"""Read-only loader and verification gates for the concept-scope sidecar (scope_v1).

The sidecar is AI-authored. Nothing here can mark a record human-verified: `ScopeRecord.human_verified` is always False and the
loader rejects any `verification_status` it does not know, so a future human status needs an explicit code change plus review.

Penalty gate (Stage 3C-1 rule): a record may let a missing ESSENTIAL concept lower completeness only if ALL hold:
  * the sidecar flag completeness_penalty_eligible is true,
  * verification_status == 'ai_reviewed_pilot' and tier_source is a manual (read-by-AI) source,
  * human_review_required is false,
  * it has at least one essential concept or group.
The loader recomputes this and never trusts the flag alone, so a heuristic-only record can never be eligible.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SIDECAR = REPO_ROOT / "data" / "evaluation" / "scope" / "scope_v1.jsonl"
DEFAULT_MANIFEST = REPO_ROOT / "data" / "evaluation" / "scope" / "scope_v1_manifest.json"
ALLOWED_STATUSES = frozenset({"ai_heuristic_draft", "ai_reviewed_pilot"})
MANUAL_SOURCES = frozenset({"manual_pilot", "manual_zero_essential"})
HEURISTIC_SOURCES = frozenset({"heuristic_v2"})


class ScopeError(Exception):
    pass


class ScopeIntegrityError(ScopeError):
    """Sidecar missing, altered (checksum mismatch), malformed or carrying an unknown status."""


class ScopeUnavailable(ScopeError):
    """No scope record for this question id."""


@dataclass(frozen=True)
class EssentialGroup:
    label: str
    concepts: Tuple[str, ...]
    min_required: int


@dataclass(frozen=True)
class Alternative:
    text: str
    basis: str


@dataclass(frozen=True)
class ScopeRecord:
    question_id: str
    question_type: str
    domain: str
    difficulty: str
    essential_concepts: Tuple[str, ...]
    essential_groups: Tuple[EssentialGroup, ...]
    supporting_concepts: Tuple[str, ...]
    background_concepts: Tuple[str, ...]
    label_concepts: Tuple[str, ...]
    added_concepts: Tuple[str, ...]
    alternatives: Tuple[Alternative, ...]
    verification_status: str
    tier_source: str
    ambiguity_flags: Tuple[str, ...]
    human_review_required: bool
    penalty_flag_in_sidecar: bool
    review_notes: str

    @property
    def human_verified(self) -> bool:
        return False                      # no record in scope_v1 is human-verified; AI review is never reported as human review

    @property
    def has_essentials(self) -> bool:
        return bool(self.essential_concepts or self.essential_groups)

    @property
    def gate_failures(self) -> Tuple[str, ...]:
        why = []
        if not self.penalty_flag_in_sidecar:
            why.append("sidecar_flag_not_eligible")
        if self.verification_status != "ai_reviewed_pilot":
            why.append("not_ai_reviewed")
        if self.tier_source not in MANUAL_SOURCES:
            why.append("tier_source_not_manual")
        if self.human_review_required:
            why.append("human_review_required")
        if not self.has_essentials:
            why.append("no_essential_requirements")
        return tuple(why)

    @property
    def penalty_eligible(self) -> bool:
        """True only for the explicitly eligible records (see module docstring). Recomputed, never trusted from the flag alone."""
        return not self.gate_failures


class ScopeStore:
    """Immutable view over the sidecar. Opens the file read-only, verifies its sha256 against the manifest, never writes."""

    def __init__(self, records: Mapping[str, ScopeRecord], sidecar_sha256: str, source: str):
        self._records = MappingProxyType(dict(records))
        self.sidecar_sha256 = sidecar_sha256
        self.source = source

    @classmethod
    def load(cls, sidecar: Path | str = DEFAULT_SIDECAR, manifest: Path | str | None = DEFAULT_MANIFEST, *, verify_checksum: bool = True) -> "ScopeStore":
        sidecar = Path(sidecar)
        try:
            raw = sidecar.read_bytes()
        except OSError as e:
            raise ScopeIntegrityError(f"cannot read scope sidecar: {e}") from e
        digest = hashlib.sha256(raw).hexdigest()
        if verify_checksum:
            if manifest is None or not Path(manifest).exists():
                raise ScopeIntegrityError("scope manifest not found; refusing to use an unverifiable sidecar")
            expected = json.loads(Path(manifest).read_text(encoding="utf-8")).get("sidecar_sha256")
            if expected != digest:
                raise ScopeIntegrityError(f"scope sidecar sha256 mismatch: manifest {str(expected)[:12]} vs file {digest[:12]}")
        recs = {}
        for n, line in enumerate(raw.decode("utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                d = json.loads(line)
                r = _parse(d)
            except (ValueError, KeyError, TypeError) as e:
                raise ScopeIntegrityError(f"malformed scope row {n}: {e}") from e
            if r.question_id in recs:
                raise ScopeIntegrityError(f"duplicate question_id {r.question_id}")
            recs[r.question_id] = r
        return cls(recs, digest, str(sidecar))

    def get(self, question_id: str) -> ScopeRecord:
        try:
            return self._records[question_id]
        except KeyError:
            raise ScopeUnavailable(f"no scope record for {question_id!r}") from None

    def __contains__(self, question_id: str) -> bool:
        return question_id in self._records

    def __len__(self) -> int:
        return len(self._records)

    def ids(self) -> Tuple[str, ...]:
        return tuple(self._records)

    def eligible_ids(self) -> Tuple[str, ...]:
        return tuple(q for q, r in self._records.items() if r.penalty_eligible)

    def records(self):
        return self._records.values()


def _parse(d: dict) -> ScopeRecord:
    status = d["verification_status"]
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"unknown verification_status {status!r} (a human status requires an explicit code change)")
    return ScopeRecord(
        question_id=d["question_id"], question_type=d["question_type"], domain=d.get("domain", ""), difficulty=d.get("difficulty", ""),
        essential_concepts=tuple(d["essential_concepts"]),
        essential_groups=tuple(EssentialGroup(g["label"], tuple(g["concepts"]), int(g["min_required"])) for g in d["essential_groups"]),
        supporting_concepts=tuple(d["supporting_concepts"]), background_concepts=tuple(d["background_concepts"]),
        label_concepts=tuple(d.get("label_concepts", ())), added_concepts=tuple(d.get("added_concepts", ())),
        alternatives=tuple(Alternative(a["text"], a["basis"]) for a in d["acceptable_alternative_explanations"]),
        verification_status=status, tier_source=d["tier_source"], ambiguity_flags=tuple(d["ambiguity_flags"]),
        human_review_required=bool(d["human_review_required"]), penalty_flag_in_sidecar=bool(d.get("completeness_penalty_eligible", False)),
        review_notes=d.get("review_notes", ""))
