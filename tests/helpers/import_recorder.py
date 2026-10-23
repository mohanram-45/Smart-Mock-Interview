"""Records every ATTEMPT to import torch / sentence_transformers / faiss in a process, and says whether the code that asked is allowed to.

10N final Windows repair. The first version attributed an attempt to the last four frames of its call stack that looked like project code. On Windows the virtual environment (`.bot`) lives INSIDE the
project folder, so third-party frames (sentence_transformers importing its own submodules, then torch) counted as project code, pushed the retrieval frames out of the last four, and a perfectly lazy
import was reported as eager. Attribution now uses ONLY frames of the application's own packages (<root>/src and <root>/main) and looks at ALL of them, so it does not depend on where Python is installed
or on how deep a library's own import chain is. An attempt is allowed when some application frame on its stack is in src/retrieval (the ranking layer) or is the engine's `_service_search`."""
import importlib.abc
import os
import sys
import traceback

WATCH = ("torch", "sentence_transformers", "faiss")
ATTEMPTS = []                       # (module name, [(path relative to the root, function), ...] application frames only, outermost first)
_SEEN = set()


def _norm(p):
    return os.path.normcase(os.path.abspath(p))


class _Recorder(importlib.abc.MetaPathFinder):
    def __init__(self, root):
        self.root = _norm(root)
        self.own = (os.path.join(self.root, "src") + os.sep, os.path.join(self.root, "main") + os.sep)
        self._cache = {}

    def _rel(self, filename):
        if filename not in self._cache:
            n = _norm(filename)
            self._cache[filename] = os.path.relpath(n, self.root).replace(os.sep, "/") if n.startswith(self.own) else None
        return self._cache[filename]

    def find_spec(self, name, path, target=None):
        if name.split(".")[0] in WATCH and name not in _SEEN:
            _SEEN.add(name)
            frames = []
            for f in traceback.extract_stack()[:-1]:
                rel = self._rel(f.filename)
                if rel:
                    frames.append((rel, f.name))
            ATTEMPTS.append((name, frames))
        return None


def install(root):
    sys.meta_path.insert(0, _Recorder(root))


def is_allowed(frames):
    return any(rel.startswith("src/retrieval/") or func == "_service_search" for rel, func in frames)


def classify(attempts):
    """(allowed, prohibited). An attempt with no application frame at all is prohibited: nothing of ours can vouch for it."""
    allowed = [a for a in attempts if is_allowed(a[1])]
    return allowed, [a for a in attempts if not is_allowed(a[1])]
