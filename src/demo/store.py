"""Thread-safe session store: in-memory working set (size cap, idle TTL) backed by one small JSON file per session.

Every state change is written atomically to `results/demo_sessions/<id>.json`, so a refresh, an idle eviction or a server restart never loses an interview. Privacy:
the files hold the candidate's own answers and the scores shown to them, nothing else (no reference answers); they stay on this machine (the folder is git-ignored),
ids are unguessable (secrets) and validated before any file access, files older than the retention period (default 14 days) are deleted, and a session can be erased
on request (`delete`). A model job that was still running when the server stopped is reported as interrupted, never left "pending" forever.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

ID_RX = re.compile(r"^demo_[0-9a-f]{20}$")


def new_id() -> str:
    return "demo_" + secrets.token_hex(10)


def default_dir() -> Path:
    env = os.environ.get("SMART_DEMO_DATA_DIR", "").strip()
    return Path(env) if env else Path(__file__).resolve().parents[2] / "results" / "demo_sessions"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{secrets.token_hex(3)}.tmp")          # unique per write: two writers never share a temp file
    try:
        tmp.write_text(text, encoding="utf-8")
        for attempt in range(6):                                  # Windows: a virus scanner or indexer can hold the target for a moment (PermissionError)
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


class DemoStore:
    def __init__(self, directory: Optional[Path] = None, *, max_sessions: int = 200, ttl_seconds: float = 6 * 3600, persist: bool = True,
                 retention_days: Optional[float] = None):
        self.dir = Path(directory) if directory else default_dir()
        self.max_sessions, self.ttl, self.persist = max_sessions, ttl_seconds, persist
        if retention_days is None:
            try:
                retention_days = float(os.environ.get("SMART_DEMO_RETENTION_DAYS", "14"))
            except ValueError:
                retention_days = 14.0
        self.retention_days = retention_days
        self._pruned = False
        self.lock = threading.RLock()
        self._s: Dict[str, Dict[str, Any]] = {}
        self._touched: Dict[str, float] = {}

    def _evict(self) -> None:
        now = time.time()
        for sid in [s for s, t in self._touched.items() if now - t > self.ttl]:
            self._s.pop(sid, None); self._touched.pop(sid, None)
        while len(self._s) > self.max_sessions:
            oldest = min(self._touched, key=self._touched.get)
            self._s.pop(oldest, None); self._touched.pop(oldest, None)

    def prune_files(self) -> int:
        """Delete session files older than the retention period. Best effort; returns the number removed."""
        removed = 0
        if not self.persist or not self.retention_days or self.retention_days <= 0:
            return 0
        cutoff = time.time() - self.retention_days * 86400
        try:
            for p in self.dir.glob("demo_*.json"):
                try:
                    if ID_RX.match(p.stem) and p.stat().st_mtime < cutoff:
                        p.unlink(); removed += 1
                except OSError:
                    continue
        except OSError:
            pass
        return removed

    def put(self, session: Dict[str, Any]) -> None:
        if not self._pruned:
            self._pruned = True
            self.prune_files()
        with self.lock:
            self._s[session["id"]] = session
            self._touched[session["id"]] = time.time()
            self._evict()

    def get(self, sid: str) -> Optional[Dict[str, Any]]:
        if not isinstance(sid, str) or not ID_RX.match(sid):
            return None
        with self.lock:
            s = self._s.get(sid)
            if s is not None:
                self._touched[sid] = time.time()
                return s
        return self._load(sid)

    def _load(self, sid: str) -> Optional[Dict[str, Any]]:
        p = self.dir / f"{sid}.json"
        try:
            s = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(s, dict) or s.get("id") != sid:
            return None
        s["restored_from_disk"] = True
        for a in s.get("answers") or []:                       # a job that died with the server must not look "running" forever
            m = (a or {}).get("modular")
            if m and m.get("status") == "pending":
                m["status"] = "interrupted"
            c = (a or {}).get("code")
            if c and c.get("status") == "pending":
                c["status"] = "interrupted"
        with self.lock:
            self._s[sid] = s
            self._touched[sid] = time.time()
        return s

    def save(self, session: Dict[str, Any]) -> bool:
        """Persist the session (any status). Failure is reported, never raised: the interview must not break because the disk is read-only."""
        if not self.persist or not isinstance(session.get("id"), str) or not ID_RX.match(session["id"]):
            return False
        try:
            with self.lock:                                       # serialise AND write under the lock so an older snapshot can never overwrite a newer one
                text = json.dumps(session, ensure_ascii=False, indent=1, default=str)
                _atomic_write(self.dir / f"{session['id']}.json", text)
            return True
        except OSError:
            return False

    def delete(self, sid: str) -> bool:
        """Erase a session from memory and disk. True if anything was removed."""
        if not isinstance(sid, str) or not ID_RX.match(sid):
            return False
        with self.lock:
            had = self._s.pop(sid, None) is not None
            self._touched.pop(sid, None)
        try:
            p = self.dir / f"{sid}.json"
            if p.exists():
                p.unlink(); had = True
        except OSError:
            pass
        return had

    def all_sessions(self) -> list:
        """Every saved session (memory first, then disk), newest first. Read-only snapshot for the history pages; corrupt or foreign files are skipped."""
        out: Dict[str, Dict[str, Any]] = {}
        with self.lock:
            out.update(self._s)
        try:
            files = [p for p in self.dir.glob("demo_*.json") if ID_RX.match(p.stem)] if self.persist else []
        except OSError:
            files = []
        for p in files:
            if p.stem in out:
                continue
            try:
                s = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(s, dict) and s.get("id") == p.stem:
                out[p.stem] = s
        return sorted(out.values(), key=lambda s: s.get("created_at") or "", reverse=True)

    def delete_all(self) -> int:
        """Erase every saved session (memory and disk). Returns how many session ids were removed."""
        ids = {s["id"] for s in self.all_sessions() if isinstance(s.get("id"), str)}
        return sum(1 for sid in ids if self.delete(sid))

    def clear(self) -> None:
        with self.lock:
            self._s.clear(); self._touched.clear()
