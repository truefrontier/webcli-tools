"""httpbin.org over plain HTTPS: GET only, to HOSTS only, no redirects followed.

webcli's host envelope covers a tool's browser pages. This tool has none: it calls urllib itself, so it holds
itself to the same rule with request_allowed() before every request. POLICY states that rule for `webcli lint`.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlsplit

from webcli.adapter import Policy, describe, host_matches

BASE_URL = "https://httpbin.org"
HOSTS = ("httpbin.org",)
TIMEOUT = 20
MAX_BYTES = 1_000_000
USER_AGENT = "webcli-tool-httpbin (+https://github.com/truefrontier/webcli-tools)"


class APIError(RuntimeError):
    """httpbin.org answered with an error, or the network failed (exit 5)."""


def request_allowed(method: str, url: str) -> bool:
    parts = urlsplit(url)
    return (method.upper() in ("GET", "HEAD") and parts.scheme == "https" and parts.port in (None, 443)
            and "@" not in parts.netloc and any(host_matches(h, parts.hostname or "") for h in HOSTS))


POLICY = Policy("httpbin", lambda request, _state: request_allowed(request.method, request.url),
                lambda request: describe(request.method, request.url))


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None  # a 3xx becomes an error: following it could leave HOSTS


_opener = urllib.request.build_opener(_NoRedirects)


def get(path: str) -> Any:
    """GET BASE_URL + path, parsed as JSON."""
    url = BASE_URL + path
    if not request_allowed("GET", url):
        raise APIError(f"Refusing GET {url}: not on {', '.join(HOSTS)}.")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with _opener.open(request, timeout=TIMEOUT) as response:
            body = response.read(MAX_BYTES + 1)  # one byte more, to tell a full answer from a cut-off one
        if len(body) > MAX_BYTES:
            raise APIError(f"httpbin.org's answer for {path} is too large (over {MAX_BYTES:,} bytes).")
        return json.loads(body)
    except urllib.error.HTTPError as exc:
        raise APIError(f"httpbin.org answered HTTP {exc.code} for {path}.") from None
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise APIError(f"Can't read {url}: {getattr(exc, 'reason', exc)}") from None


def ip() -> dict:
    """{ip}: the address httpbin.org sees you calling from."""
    return {"ip": get("/ip")["origin"]}


def headers() -> list[dict]:
    """The request headers httpbin.org received, as rows {name, value}, sorted by name."""
    return [{"name": name, "value": value} for name, value in sorted(get("/headers")["headers"].items())]


def uuid() -> dict:
    """{uuid}: a random UUID4 from httpbin.org."""
    return {"uuid": get("/uuid")["uuid"]}
