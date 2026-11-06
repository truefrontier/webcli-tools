"""www.example.com (webcli yourtool): read-only. Identity provider "yourtool" (yourtool:default).

A webcli tool imports from webcli.adapter and its own package, nothing else. Every fact in ADAPTER is also in
webcli-tool.toml, and the two must agree: `webcli lint yourtool` checks.
"""

from __future__ import annotations

from webcli.adapter import Site, Strategy
from webcli_tool_yourtool.endpoints import HOSTS


def _cli():
    from webcli_tool_yourtool.cli import group

    return group


async def _login(timeout: int, on_state=lambda _state: None) -> dict:
    from webcli_tool_yourtool import fetch

    return await fetch.login(timeout, on_state)


ADAPTER = Site(
    name="yourtool",
    kind="data",
    provider="yourtool",
    summary="www.example.com, read-only: page (its headings and links), status",
    cli=_cli,
    fetch="webcli_tool_yourtool.fetch",
    ops=("status", "page"),
    verbs={"status": Strategy.COOKIE, "page": Strategy.COOKIE},
    login=_login,
    status_op="status",
    adapter_api=1,
    version="0.1.0",
    hosts=HOSTS,
)
