"""`webcli httpbin`: httpbin.org, read-only, over plain HTTPS. No browser, no identity."""

from __future__ import annotations

import click

from webcli.adapter import (
    EXIT_API,
    EXIT_OK,
    add_agent_help,
    agent_output_options,
    die,
    emit_record,
    emit_rows,
)
from webcli_tool_httpbin import api

NOTES = [
    "A demo community tool from the webcli-tools library. Plain HTTPS GETs to httpbin.org: no browser, no "
    "identity, no daemon.",
    "ip: {ip}. headers: rows {name, value}. uuid: {uuid}.",
    "A network or HTTP error exits 5. Redirects aren't followed.",
]
WRITES = ["None. Read-only: every request is a GET to httpbin.org."]


@click.group("httpbin")
def group() -> None:
    """httpbin.org, read-only demo (a community tool). No sign-in."""


def _call(op):
    try:
        return op()
    except api.APIError as exc:
        die(str(exc), EXIT_API)


@group.command("ip")
@agent_output_options(rows=False)
def ip_cmd(fmt, quiet) -> None:
    """The public IP address httpbin.org sees you calling from."""
    emit_record("httpbin ip", _call(api.ip), fmt)
    raise SystemExit(EXIT_OK)


@group.command("headers")
@agent_output_options()
def headers_cmd(fmt, compact, select, quiet, as_csv) -> None:
    """The request headers httpbin.org received from this tool."""
    emit_rows(_call(api.headers), title="httpbin: headers", fields=["name", "value"], compact_fields=("name",),
              columns=["name", "value"], noun="headers", fmt=fmt, compact=compact, select=select, quiet=quiet,
              as_csv=as_csv)
    raise SystemExit(EXIT_OK)


@group.command("uuid")
@agent_output_options(rows=False)
def uuid_cmd(fmt, quiet) -> None:
    """A random UUID (version 4) from httpbin.org."""
    emit_record("httpbin uuid", _call(api.uuid), fmt)
    raise SystemExit(EXIT_OK)


add_agent_help(group, notes=NOTES, writes=WRITES)
