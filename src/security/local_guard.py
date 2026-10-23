"""Stage 13: who may call the legacy mutating endpoints (email a report, download a report).

The apps are local-first: the browser pages and the API run on the same computer. A request is accepted when
  * it comes from a page on this computer (Origin is localhost / 127.0.0.1 / [::1], the request's own origin, or an origin listed in SMART_ALLOWED_ORIGINS), or
  * it carries NO Origin header (curl, scripts) AND the TCP peer is the loopback interface.
A request from any other web page (cross-site request) or from another machine is refused with 403. If SMART_REPORT_TOKEN is set, every request must also send it in
`X-Report-Token` (constant-time comparison); use that when the API is deliberately exposed beyond this computer.
"""
from __future__ import annotations

import hmac
import ipaddress
import os
import re
import time
from collections import deque
from typing import Deque, Dict, List, Optional
from urllib.parse import urlsplit

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}
_RECIPIENT = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$")


def extra_origins() -> List[str]:
    return [o.strip().rstrip("/").lower() for o in os.environ.get("SMART_ALLOWED_ORIGINS", "").split(",") if o.strip()]


def cors_origins() -> List[str]:
    """Origins for Flask-CORS: local pages only (plus SMART_ALLOWED_ORIGINS). Never '*'."""
    base: List[str] = []
    for host in ("localhost", "127.0.0.1"):
        for port in (3000, 5000, 5050):
            base.append(f"http://{host}:{port}")
    return base + extra_origins()


def _gateway_from_route(text: str) -> Optional[str]:
    """The default gateway in the text of /proc/net/route (hex, little-endian), or None."""
    for line in (text or "").splitlines()[1:]:
        f = line.split()
        if len(f) >= 3 and f[1] == "00000000" and re.fullmatch(r"[0-9A-Fa-f]{8}", f[2]):
            return str(ipaddress.ip_address(int(f[2], 16).to_bytes(4, "little")))
    return None


def docker_gateway() -> Optional[str]:
    try:
        with open("/proc/net/route", encoding="ascii") as fh:
            return _gateway_from_route(fh.read())
    except OSError:
        return None


def trusted_peers(route_text: Optional[str] = None) -> set:
    """Peers treated like this computer, by EXACT address only (never a network range):
      * SMART_TRUSTED_PEERS - comma-separated single IP addresses, set deliberately by the operator;
      * the container's default gateway when SMART_TRUST_DOCKER_GATEWAY=1 (set only in the Docker image). With the port published to the host's 127.0.0.1 (docker-compose.yml)
        the host's browser reaches the app through that one address. Other containers on the compose network and every other private address stay untrusted.
    If the port is ever published beyond loopback, set SMART_REPORT_TOKEN as well: a published port can make remote clients appear as the gateway."""
    out = set()
    for item in os.environ.get("SMART_TRUSTED_PEERS", "").split(","):
        try:
            out.add(str(ipaddress.ip_address(item.strip())))
        except ValueError:
            pass
    if os.environ.get("SMART_TRUST_DOCKER_GATEWAY") == "1":
        gw = _gateway_from_route(route_text) if route_text is not None else docker_gateway()
        if gw:
            out.add(gw)
    out.discard("0.0.0.0")
    return out


def is_loopback(addr: Optional[str]) -> bool:
    """True for this computer, or for an explicitly trusted peer (see trusted_peers)."""
    try:
        ip = ipaddress.ip_address((addr or "").split("%")[0])
    except ValueError:
        return False
    return ip.is_loopback or str(ip) in trusted_peers()


def origin_allowed(origin: str, own_origin: str = "") -> bool:
    o = (origin or "").strip().rstrip("/").lower()
    if not o or o == "null":
        return False
    if own_origin and o == own_origin.rstrip("/").lower():
        return True
    if o in extra_origins():
        return True
    parts = urlsplit(o)
    return parts.scheme in ("http", "https") and (parts.hostname or "") in {"localhost", "127.0.0.1", "::1"}


def check_request(request) -> Optional[str]:
    """Return None when the request may proceed, else a short reason (the caller answers 403)."""
    token = os.environ.get("SMART_REPORT_TOKEN", "")
    if token and not hmac.compare_digest(token.encode(), (request.headers.get("X-Report-Token") or "").encode()):
        return "missing_or_wrong_token"
    origin = request.headers.get("Origin")
    if origin is not None:
        return None if origin_allowed(origin, request.host_url) else "origin_not_allowed"
    if token:
        return None
    return None if is_loopback(request.remote_addr) else "not_local"


def valid_recipient(address: str) -> bool:
    """One plain mailbox: no names, no lists, no control characters or header injection, RFC-length limits."""
    a = address or ""
    if not a or len(a) > 254 or a != a.strip() or any(ord(c) < 33 or ord(c) == 127 for c in a):
        return False
    return bool(_RECIPIENT.fullmatch(a)) and ".." not in a and not a.split("@")[0].startswith(".") and not a.split("@")[0].endswith(".")


class SendLimiter:
    """In-memory limits on outgoing mail: one send per report per `per_report_s`, and `max_total` sends per `window_s` overall."""

    def __init__(self, per_report_s: int = 60, max_total: int = 5, window_s: int = 600):
        self.per_report_s, self.max_total, self.window_s = per_report_s, max_total, window_s
        self._last: Dict[str, float] = {}
        self._all: Deque[float] = deque()

    def allow(self, key: str, now: Optional[float] = None) -> Optional[int]:
        """None = allowed (and recorded); otherwise the seconds to wait."""
        now = time.monotonic() if now is None else now
        while self._all and now - self._all[0] > self.window_s:
            self._all.popleft()
        wait_key = self.per_report_s - (now - self._last.get(key, -1e12))
        if wait_key > 0:
            return int(wait_key) + 1
        if len(self._all) >= self.max_total:
            return int(self.window_s - (now - self._all[0])) + 1
        self._last[key] = now
        self._all.append(now)
        return None
