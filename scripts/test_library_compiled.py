"""library.py check refuses tracked compiled Python: a __pycache__/ folder, or a .pyc, .pyo, .pyd or .so file.

Each test builds a throwaway git repo in tmp_path and points library.py at it, never at this repo's history.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import library


def git(root: Path, *args: str) -> None:
    # Leave out the hooks and signing that your own git config may set.
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Test", "-c", "user.email=test@example.com",
                    "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
                   check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "repo"
    pkg = root / "tools" / "acme" / "webcli_tool_acme"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("ADAPTER = None\n")
    (root / ".gitignore").write_text("__pycache__/\n")
    git(root, "init", "-q")
    git(root, "add", "--all")
    git(root, "commit", "-q", "-m", "a library with one tool")
    monkeypatch.setattr(library, "ROOT", root)
    return root


def track(root: Path, rel: str, *, force: bool = False) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00compiled")
    git(root, "add", *(["-f"] if force else []), rel)


def test_a_clean_library_passes(repo):
    assert library.tracked_compiled() == []


def test_python_s_own_cache_on_disk_is_not_tracked_so_it_passes(repo):
    cache = repo / "tools/acme/webcli_tool_acme/__pycache__"
    cache.mkdir()
    (cache / "__init__.cpython-312.pyc").write_bytes(b"\x00")
    assert library.tracked_compiled() == []


def test_a_force_added_cache_is_refused(repo):
    # The case webcli's lint can't tell from Python's own cache, and the one install trips on.
    track(repo, "tools/acme/webcli_tool_acme/__pycache__/__init__.cpython-312.pyc", force=True)
    problems = library.tracked_compiled()
    assert len(problems) == 1
    assert problems[0].startswith("tools/acme/webcli_tool_acme/__pycache__/__init__.cpython-312.pyc: ")


@pytest.mark.parametrize("rel", ["tools/acme/webcli_tool_acme/helper.pyc", "tools/acme/webcli_tool_acme/old.pyo",
                                 "tools/acme/webcli_tool_acme/fast.cpython-312-darwin.so",
                                 "tools/acme/webcli_tool_acme/fast.cp312-win_amd64.pyd",
                                 "TEMPLATE/webcli_tool_yourtool/x.PYC", "scripts/__pycache__/notes.txt"])
def test_compiled_files_are_refused_anywhere_in_the_repo(repo, rel):
    track(repo, rel, force=True)
    assert [p.split(": ", 1)[0] for p in library.tracked_compiled()] == [rel]


@pytest.mark.parametrize("rel", ["docs/sonnet.md", "tools/acme/notes.so.txt", "tools/acme/pycache_notes.md",
                                 "tools/acme/webcli_tool_acme/parse.py"])
def test_names_that_only_look_compiled_pass(repo, rel):
    track(repo, rel)
    assert library.tracked_compiled() == []


def test_a_path_with_spaces_is_named_as_it_is(repo):
    track(repo, "tools/acme/odd dir/x.pyc", force=True)
    assert library.tracked_compiled()[0].startswith("tools/acme/odd dir/x.pyc: ")
