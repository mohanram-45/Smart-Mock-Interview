"""A scripted interview used both to RECORD the pre-change golden baseline and to COMPARE after the change."""
import random

VOLATILE = {"session_id", "started_at", "interview_id", "timestamp", "generated_at", "ended_at"}


def scrub(o):
    if isinstance(o, dict):
        return {k: ("<volatile>" if k in VOLATILE else scrub(v)) for k, v in o.items()}
    if isinstance(o, list):
        return [scrub(x) for x in o]
    return o


def run(client, payload_extra=None):
    """Drive one full legacy interview (custom domains with legacy labels, fixed-curriculum model). Returns the list of
    (label, status, scrubbed-json) steps."""
    random.seed(20261014)
    steps = []

    def rec(label, resp):
        steps.append((label, resp.status_code, scrub(resp.get_json())))
        return resp.get_json()

    rec("GET /", client.get("/"))
    rec("GET /health", client.get("/health"))
    rec("GET /api/roles", client.get("/api/roles"))
    rec("GET /api/domains", client.get("/api/domains"))
    rec("GET /api/models", client.get("/api/models"))
    body = {"role": "Custom Interview", "custom_domains": ["Python", "SQL"], "model": "bilstm"}
    body.update(payload_extra or {})
    start = rec("POST /api/start-interview", client.post("/api/start-interview", json=body))
    sid = start["session_id"]
    rec("GET /api/current-question", client.get(f"/api/current-question?session_id={sid}"))
    rec("GET /api/repeat-question", client.get(f"/api/repeat-question?session_id={sid}"))
    rec("GET /api/session-status", client.get(f"/api/session-status?session_id={sid}"))
    rec("POST /api/submit-answer", client.post("/api/submit-answer", json={"session_id": sid, "answer": "a model learns patterns from data"}))
    rec("POST /api/next-question", client.post("/api/next-question", json={"session_id": sid}))
    rec("POST /api/skip-question", client.post("/api/skip-question", json={"session_id": sid}))
    rec("POST /api/check-round-completion", client.post("/api/check-round-completion", json={"session_id": sid}))
    rec("POST /api/submit-answer (2)", client.post("/api/submit-answer", json={"session_id": sid, "answer": "index joins and window functions"}))
    rec("GET /api/session-status (2)", client.get(f"/api/session-status?session_id={sid}"))
    # error paths
    rec("POST start invalid role", client.post("/api/start-interview", json={"role": "Wizard"}))
    rec("POST start invalid model", client.post("/api/start-interview", json={"role": "Python Developer", "model": "gpt"}))
    rec("POST start no domains", client.post("/api/start-interview", json={"role": "Custom Interview", "custom_domains": []}))
    rec("POST start unknown domain", client.post("/api/start-interview", json={"role": "Custom Interview", "custom_domains": ["Underwater Basket Weaving"]}))
    rec("GET current-question bad session", client.get("/api/current-question?session_id=nope"))
    rec("POST submit empty answer", client.post("/api/submit-answer", json={"session_id": sid, "answer": "   "}))
    rec("POST submit bad session", client.post("/api/submit-answer", json={"session_id": "nope", "answer": "x"}))
    rec("GET unknown route", client.get("/api/does-not-exist"))
    return steps
