"""Offline tests for webcli httpbin: `webcli test tools/httpbin` runs them with the network blocked, and so does the
library's CI (plain pytest works too). Each test is a function that takes no arguments.

tests/fixtures/*.json are httpbin.org's answers, recorded and scrubbed (the IP is a documentation address).
"""

from __future__ import annotations

import io
import json
import urllib.error
from contextlib import contextmanager
from pathlib import Path

from webcli_tool_httpbin import ADAPTER, api

FIXTURES = Path(__file__).parent / "fixtures"


class FakeOpener:
    """Answers each path from tests/fixtures/<path>.json, or with `error`; records every URL asked for."""

    def __init__(self, error: Exception | None = None) -> None:
        self.urls, self.error = [], error

    def open(self, request, timeout):
        self.urls.append(request.full_url)
        if self.error:
            raise self.error
        return io.BytesIO((FIXTURES / f"{request.full_url.rsplit('/', 1)[1]}.json").read_bytes())


@contextmanager
def answering(opener: FakeOpener):
    saved, api._opener = api._opener, opener
    try:
        yield opener
    finally:
        api._opener = saved


def test_ip_reads_origin():
    with answering(FakeOpener()) as opener:
        assert api.ip() == {"ip": "203.0.113.7"}
    assert opener.urls == ["https://httpbin.org/ip"]


def test_headers_are_sorted_rows():
    with answering(FakeOpener()):
        rows = api.headers()
    assert [r["name"] for r in rows] == ["Accept", "Accept-Encoding", "Host", "User-Agent"]
    assert rows[2] == {"name": "Host", "value": "httpbin.org"}


def test_uuid():
    with answering(FakeOpener()):
        assert api.uuid() == {"uuid": "0b5d5e1e-8f8a-4c47-9d1e-2f0a6f3c1b2a"}


def test_errors_become_api_errors():
    for error in (urllib.error.HTTPError("https://httpbin.org/ip", 503, "busy", {}, None),
                  urllib.error.URLError("no network"), ValueError("not json")):
        with answering(FakeOpener(error)):
            try:
                api.ip()
            except api.APIError:
                pass
            else:
                raise AssertionError(f"{error!r} didn't become an APIError")


def test_only_https_gets_to_httpbin_are_allowed():
    assert api.request_allowed("GET", "https://httpbin.org/ip")
    assert not api.request_allowed("POST", "https://httpbin.org/post")
    assert not api.request_allowed("DELETE", "https://httpbin.org/delete")
    assert not api.request_allowed("GET", "http://httpbin.org/ip")
    assert not api.request_allowed("GET", "https://httpbin.org:8443/ip")
    assert not api.request_allowed("GET", "https://evil.example@httpbin.org/ip")
    assert not api.request_allowed("GET", "https://httpbin.org.evil.example/ip")


def test_redirects_are_not_followed():
    assert api._NoRedirects().redirect_request(None, None, 302, "Found", {}, "https://elsewhere.example/") is None


def test_every_fixture_is_json():
    for path in FIXTURES.glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))


def test_the_adapter_is_read_only():
    assert ADAPTER.writes == frozenset() and ADAPTER.sends_to_people == frozenset()
    assert ADAPTER.hosts == ("httpbin.org",)
