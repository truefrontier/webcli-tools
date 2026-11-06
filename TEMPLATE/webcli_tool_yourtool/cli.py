"""`webcli yourtool`: www.example.com, read-only, from your own hidden Chrome (yourtool:default)."""

from __future__ import annotations

import click

from webcli.adapter import (
    EXIT_AUTH,
    EXIT_NOT_FOUND,
    EXIT_OK,
    add_agent_help,
    agent_output_options,
    call,
    die,
    emit_record,
    emit_rows,
    login_hint,
    site_group,
)
from webcli_tool_yourtool import ADAPTER as SITE
from webcli_tool_yourtool.endpoints import DEFAULT_LIMIT, MAX_LIMIT

NOTES = [
    "Runs as yourtool:default in its own hidden Chrome: no window, no focus change. A person signs it in once "
    "with `webcli identity login yourtool:default`.",
    "Reads https://www.example.com/ with GET requests only; every other request is aborted.",
    "page: rows {kind (heading or link), text, url}. No rows exits 3.",
]
WRITES = ["None. Read-only."]

group = site_group(SITE, "www.example.com, read-only (a community tool). Identity yourtool:default.")


@group.command("status")
@agent_output_options(rows=False)
def status_cmd(fmt, quiet) -> None:
    """Whether yourtool:default can read www.example.com signed in (exit 4 if the page shows a sign-in form)."""
    info = call(SITE, "status")
    emit_record("yourtool session", info, fmt)
    if not info["signedIn"]:
        die("www.example.com shows a sign-in form.", EXIT_AUTH, hint=login_hint())
    raise SystemExit(EXIT_OK)


@group.command("page")
@click.option("--limit", default=DEFAULT_LIMIT, show_default=True, type=click.IntRange(1, MAX_LIMIT),
              help="Max rows.")
@agent_output_options()
def page_cmd(limit, fmt, compact, select, quiet, as_csv) -> None:
    """The page's headings, then its links (READ-ONLY). Exit 3 when there are none."""
    rows = call(SITE, "page", limit)
    if not rows:
        die("The page showed no headings or links.", EXIT_NOT_FOUND)
    emit_rows(rows, title="yourtool: page", fields=["kind", "text", "url"], compact_fields=("kind", "text"),
              columns=["kind", "text", "url"], noun="rows", fmt=fmt, compact=compact, select=select, quiet=quiet,
              as_csv=as_csv)
    raise SystemExit(EXIT_OK)


add_agent_help(group, notes=NOTES, writes=WRITES)
