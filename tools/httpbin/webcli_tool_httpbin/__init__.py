"""httpbin.org (webcli httpbin): a read-only demo tool. Plain HTTPS GETs, no browser, no sign-in (identity "none").

A webcli tool imports from webcli.adapter and its own package, nothing else. Every fact in ADAPTER is also in
webcli-tool.toml, and the two must agree: `webcli lint tools/httpbin` checks.
"""

from __future__ import annotations

from webcli.adapter import NO_IDENTITY, Site, Strategy
from webcli_tool_httpbin.api import HOSTS


def _cli():
    from webcli_tool_httpbin.cli import group

    return group


ADAPTER = Site(
    name="httpbin",
    kind="data",
    provider=NO_IDENTITY,
    summary="httpbin.org, read-only demo: your public IP, the headers it sees, a fresh UUID. No sign-in, no browser",
    cli=_cli,
    fetch="webcli_tool_httpbin.api",
    ops=(),
    verbs={"ip": Strategy.PUBLIC, "headers": Strategy.PUBLIC, "uuid": Strategy.PUBLIC},
    status_op=None,
    adapter_api=1,
    version="0.1.0",
    hosts=HOSTS,
)
