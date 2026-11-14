"""library.py's own tests: `python scripts/library.py check` runs them when pytest is installed.

The ones that need git build a throwaway repo in tmp_path and point library.py at it, never at this repo's history.
The ones that need webcli skip without it (CI installs it).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import library
from library import keeps_verified

NEW = {"name": "acmenotes", "version": "0.1.0", "sha256": "a" * 64}  # what `pin` is about to write
OLD = {**NEW, "verified": True}  # the entry it replaces, which a maintainer verified


def test_same_version_with_changed_files_is_not_verified():
    assert keeps_verified(OLD, {**NEW, "sha256": "b" * 64}) is False


def test_the_same_files_stay_verified():
    assert keeps_verified(OLD, NEW) is True


def test_a_new_version_is_not_verified():
    assert keeps_verified(OLD, {**NEW, "version": "0.2.0", "sha256": "b" * 64}) is False


# --- a throwaway library repo ---------------------------------------------------------------------------------

MANIFEST = 'name = "{name}"\nversion = "{version}"\nsummary = "Notes from {name}."\n'
# tree_sha256 of tools/acme as Repo.tool("acme") writes it, worked out by hand from the format in schema/index.md.
ACME_SHA256 = "61ef61de018cad060fa33d6069cb93ba0be46f8b047a98b9eb2f9fedc570d7fd"


class Repo:
    """A git repo that library.py treats as this library. It starts with an index.json that lists no tools."""

    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir()
        self.git("init", "-q")
        self.write("index.json", json.dumps({"repo": library.REPO, "archive": library.ARCHIVE, "tools": [],
                                             "revoked": []}))
        self.commit("an empty library")

    def git(self, *args: str) -> str:
        # Leave out the hooks and signing that your own git config may set.
        config = ["-c", "user.name=Test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false",
                  "-c", "core.hooksPath=/dev/null"]
        return subprocess.run(["git", "-C", str(self.root), *config, *args], check=True, capture_output=True,
                              text=True).stdout

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self, message: str) -> str:
        self.git("add", "--all")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD").strip()

    def tool(self, name: str, version: str = "0.1.0") -> str:
        """Commit tools/<name>: a manifest, a package, and one passing test. Returns the commit."""
        self.write(f"tools/{name}/webcli-tool.toml", MANIFEST.format(name=name, version=version))
        self.write(f"tools/{name}/webcli_tool_{name}/__init__.py", "ADAPTER = None\n")
        self.write(f"tools/{name}/tests/test_{name}.py", "def test_it():\n    pass\n")
        return self.commit(f"{name} {version}")

    def index(self) -> dict:
        return json.loads((self.root / "index.json").read_text(encoding="utf-8"))

    def entry(self, name: str) -> dict:
        return next(t for t in self.index()["tools"] if t["name"] == name)

    def add_to_index(self, entry: dict) -> None:
        index = self.index()
        index["tools"].append(entry)
        self.write("index.json", json.dumps(index))

    def set_in_index(self, name: str, **changes) -> None:
        index = self.index()
        next(t for t in index["tools"] if t["name"] == name).update(changes)
        self.write("index.json", json.dumps(index))


@pytest.fixture
def repo(tmp_path, monkeypatch) -> Repo:
    monkeypatch.setattr(library, "ROOT", tmp_path / "repo")
    monkeypatch.setattr(library, "INDEX", tmp_path / "repo" / "index.json")
    return Repo(tmp_path / "repo")


@pytest.fixture
def no_webcli(monkeypatch) -> None:
    """Make `import webcli` fail, as it does on a machine without webcli."""
    for module in [m for m in sys.modules if m.startswith("webcli.")] + ["webcli"]:
        monkeypatch.setitem(sys.modules, module, None)


# A well-formed official built-in's catalog entry.
BUILTIN = {"name": "acmemail", "version": "1.0.0", "summary": "Acme Mail.", "tier": "official", "builtin": True,
           "verified": True, "requires_webcli": ">=1.0.0,<2", "source": "core", "identity": "acme",
           "hosts": ["mail.example.com"], "commands": [{"name": "inbox", "strategy": "cookie", "writes": False}],
           "docs": library.WEBCLI_DOCS + "acme.md"}


# --- tree_sha256 ----------------------------------------------------------------------------------------------

def test_tree_sha256_is_the_pinned_hash_format(repo):
    assert library.tree_sha256(repo.tool("acme"), "tools/acme") == ACME_SHA256


def test_tree_sha256_agrees_with_the_hash_webcli_checks_at_install(repo):
    index_client = pytest.importorskip("webcli.core.index_client")
    repo.tool("acme")
    assert index_client.tree_sha256(repo.root / "tools/acme") == ACME_SHA256


def test_tree_sha256_reads_the_commit_not_the_working_tree(repo):
    commit = repo.tool("acme")
    repo.write("tools/acme/webcli_tool_acme/__init__.py", "ADAPTER = 'changed'\n")
    assert library.tree_sha256(commit, "tools/acme") == ACME_SHA256
    assert library.tree_sha256(repo.commit("change acme"), "tools/acme") != ACME_SHA256


def test_tree_sha256_refuses_a_symlink(repo):
    repo.tool("acme")
    (repo.root / "tools/acme/link").symlink_to("webcli-tool.toml")
    with pytest.raises(ValueError, match="^tools/acme/link is a link or special file"):
        library.tree_sha256(repo.commit("a link"), "tools/acme")


# --- check_builtin --------------------------------------------------------------------------------------------

def test_a_well_formed_builtin_passes():
    assert library.check_builtin(BUILTIN, "x") == []


def test_a_builtin_without_docs_passes():
    assert library.check_builtin({k: v for k, v in BUILTIN.items() if k != "docs"}, "x") == []


@pytest.mark.parametrize("key", ["commit", "sha256", "path"])
def test_a_builtin_never_pins_files(key):
    assert library.check_builtin({**BUILTIN, key: "x"}, "x") == [
        "x: a built-in needs exactly builtin, commands, hosts, identity, name, requires_webcli, source, summary, "
        "tier, verified, version, and optionally docs (never commit, sha256, or path)"]


@pytest.mark.parametrize("change, bad", [
    ({"name": "Acme-Mail"}, "name"),
    ({"version": "1.0"}, "version"),
    ({"tier": "community"}, "tier"),
    ({"verified": False}, "verified"),
    ({"source": "pypi"}, "source"),
    ({"identity": "Acme"}, "identity"),
    ({"hosts": "mail.example.com"}, "hosts"),
    ({"commands": [{"name": "inbox", "strategy": "magic", "writes": False}]}, "commands"),
    ({"commands": [{"name": "inbox", "strategy": "cookie"}]}, "commands"),
    ({"docs": "https://example.com/acme.md"}, "docs"),
])
def test_a_builtin_with_a_bad_field_is_named(change, bad):
    assert library.check_builtin({**BUILTIN, **change}, "x") == [
        f'x: bad {bad} (a built-in is tier "official", source "core", verified true)']


# --- pin, and check_index on what it writes -------------------------------------------------------------------

def test_pin_writes_an_entry_check_index_accepts(repo):
    commit = repo.tool("acme")
    assert library.pin("acme") == 0
    assert repo.index()["tools"] == [{"name": "acme", "version": "0.1.0", "summary": "Notes from acme.",
                                      "commit": commit, "sha256": ACME_SHA256, "path": "tools/acme",
                                      "tier": "community", "verified": False}]
    assert library.check_index() == []


def test_pin_keeps_verified_while_the_files_are_unchanged(repo):
    repo.tool("acme")
    library.pin("acme")
    repo.set_in_index("acme", verified=True)  # a maintainer reviewed it
    repo.write("README.md", "The library.\n")
    unrelated = repo.commit("a commit that leaves acme alone")
    assert library.pin("acme") == 0
    assert (repo.entry("acme")["commit"], repo.entry("acme")["verified"]) == (unrelated, True)

    repo.write("tools/acme/webcli_tool_acme/__init__.py", "ADAPTER = 'changed'\n")
    changed = repo.commit("change acme, same version")
    assert library.pin("acme") == 0
    assert (repo.entry("acme")["commit"], repo.entry("acme")["verified"]) == (changed, False)


def test_pin_refuses_a_manifest_named_for_another_tool(repo):
    repo.write("tools/acme/webcli-tool.toml", MANIFEST.format(name="other", version="0.1.0"))
    repo.commit("misnamed")
    assert library.pin("acme") == 1
    assert repo.index()["tools"] == []


def test_pin_leaves_a_builtin_to_the_builtins_command(repo):
    repo.add_to_index({**BUILTIN, "name": "acme"})
    repo.tool("acme")
    assert library.pin("acme") == 1
    assert repo.index()["tools"] == [{**BUILTIN, "name": "acme"}]


def test_check_index_catches_a_hash_that_doesnt_match(repo):
    commit = repo.tool("acme")
    library.pin("acme")
    repo.set_in_index("acme", sha256="0" * 64)
    assert library.check_index() == [
        f"index.json tool 'acme': sha256 doesn't match tools/acme at {commit[:12]} (it is {ACME_SHA256}); "
        f"run `python scripts/library.py pin acme {commit}`"]


def test_check_index_catches_a_commit_outside_this_branch(repo):
    repo.tool("acme")
    library.pin("acme")
    repo.set_in_index("acme", commit="0" * 40)
    assert library.check_index() == ["index.json tool 'acme': commit 000000000000 isn't in this branch's history"]


# --- check_index refuses the names webcli reserves ------------------------------------------------------------

def refused(name: str) -> str:
    return (f"index.json tool {name!r}: webcli won't load a tool by this name: it's one of webcli's commands, a "
            "built-in site, or the provider a built-in signs in as")


@pytest.mark.parametrize("name", ["feed", "tools", "none"])
def test_check_index_refuses_a_webcli_command(repo, name):
    repo.tool(name)
    library.pin(name)
    assert library.check_index() == [refused(name)]


@pytest.mark.parametrize("name", ["feed", "tools", "none"])
def test_check_index_refuses_a_webcli_command_without_webcli(repo, no_webcli, name):
    repo.tool(name)
    library.pin(name)
    assert library.check_index() == [refused(name)]


def test_check_index_refuses_the_provider_a_listed_builtin_signs_in_as(repo, no_webcli):
    repo.tool("acme")
    library.pin("acme")
    repo.add_to_index(BUILTIN)  # acmemail signs in as "acme"
    assert library.check_index() == [refused("acme")]


@pytest.mark.parametrize("name", ["muse", "meta", "walkie"])
def test_check_index_refuses_builtins_and_providers_only_webcli_knows(repo, name):
    # muse (provider "meta") and walkie aren't data sites, so index.json doesn't list them.
    pytest.importorskip("webcli.sites")
    repo.tool(name)
    library.pin(name)
    assert library.check_index() == [refused(name)]


def test_the_copied_core_commands_match_webcli():
    manifest_schema = pytest.importorskip("webcli.core.manifest_schema")
    assert library.CORE_COMMANDS == manifest_schema.CORE_COMMANDS


# --- check_tool, with a stand-in webcli -----------------------------------------------------------------------

@pytest.fixture
def fake_webcli(tmp_path, monkeypatch):
    """Put a `webcli` on PATH whose `lint` and `test` pass, unless named in `failing`."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")

    def install(*failing: str) -> None:
        script = bin_dir / "webcli"
        script.write_text("#!/bin/sh\n" + "".join(f'[ "$1" = {verb} ] && exit 1\n' for verb in failing) + "exit 0\n")
        script.chmod(0o755)

    install()
    return install


def test_check_tool_passes_a_tool_whose_checks_pass(repo, fake_webcli):
    repo.tool("acme")
    assert library.check_tool(repo.root / "tools/acme") == []


@pytest.mark.parametrize("verb", ["lint", "test"])
def test_check_tool_reports_a_failing_webcli_step(repo, fake_webcli, verb):
    repo.tool("acme")
    fake_webcli(verb)
    assert library.check_tool(repo.root / "tools/acme") == [
        f"tools/acme: `webcli {verb}` failed (its output is above)"]


def test_check_tool_reports_failing_tests(repo, fake_webcli):
    repo.tool("acme")
    repo.write("tools/acme/tests/test_acme.py", "def test_it():\n    assert False\n")
    assert library.check_tool(repo.root / "tools/acme") == ["tools/acme: pytest failed (its output is above)"]


def test_check_tool_wants_the_folder_named_for_the_tool(repo, fake_webcli):
    repo.tool("acme")
    repo.write("tools/acme/webcli-tool.toml", MANIFEST.format(name="other", version="0.1.0"))
    assert library.check_tool(repo.root / "tools/acme") == [
        "tools/acme: its manifest's name is 'other'; the folder must be tools/<name>"]


def test_check_tool_reports_a_manifest_it_cant_read(repo, fake_webcli):
    repo.tool("acme")
    repo.write("tools/acme/webcli-tool.toml", "name = \n")
    problems = library.check_tool(repo.root / "tools/acme")
    assert len(problems) == 1 and problems[0].startswith("tools/acme: can't read webcli-tool.toml: ")


# --- check_secrets --------------------------------------------------------------------------------------------

def test_check_secrets_passes_a_clean_repo(repo):
    pytest.importorskip("webcli.scaffold.checks")
    repo.tool("acme")
    assert library.check_secrets() == []


def test_check_secrets_finds_a_token_outside_the_tool_folders(repo):
    pytest.importorskip("webcli.scaffold.checks")
    token = "gh" + "p_" + "a1" * 18  # put together here, so this file doesn't hold one
    repo.write("docs/notes.md", f"Release with {token}\n")
    assert library.check_secrets() == ["docs/notes.md:1: looks like a GitHub token"]
