"""The library's own checks, and pinning a tool in index.json.

    python scripts/library.py check               # what CI runs: index.json, every tool and TEMPLATE, secrets
    python scripts/library.py pin NAME [COMMIT]   # point NAME's index.json entry at COMMIT (default HEAD)

It needs git, and webcli 1.0 or later (`webcli lint` and `webcli test`) on PATH and importable. `check` also runs
pytest in each tool's folder when pytest is installed.

The sha256 an index entry pins is the one `webcli tools install` checks (tree_sha256 in webcli's
webcli/core/index_client.py): sha256 over "<path>\\0<sha256 of the file's bytes>\\n" for each file in the tool's
folder at that commit, sorted by path (relative to the folder, "/"-separated). schema/index.md has the format.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.json"
REPO = "https://github.com/truefrontier/webcli-tools"
ARCHIVE = "https://codeload.github.com/truefrontier/webcli-tools/tar.gz/{commit}"
NAME = re.compile(r"[a-z][a-z0-9]{1,31}")
VERSION = re.compile(r"\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?")
HEX40, HEX64 = re.compile(r"[0-9a-f]{40}"), re.compile(r"[0-9a-f]{64}")
ENTRY_KEYS = {"name", "version", "summary", "commit", "sha256", "path", "tier", "verified"}


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True).stdout


def tree_sha256(commit: str, path: str) -> str:
    """The pinned hash of `path`'s files at `commit`, read from `git archive` (what GitHub's tarball holds too)."""
    data = subprocess.run(["git", "-C", str(ROOT), "archive", "--format=tar", commit, "--", path],
                          check=True, capture_output=True).stdout
    prefix, files = path.rstrip("/") + "/", []
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for member in tar:
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError(f"{member.name} is a link or special file; a tool holds regular files only")
            files.append((member.name.removeprefix(prefix), hashlib.sha256(tar.extractfile(member).read()).hexdigest()))
    if not files:
        raise ValueError(f"{path} has no files at {commit[:12]}")
    digest = hashlib.sha256()
    for rel, file_hash in sorted(files):
        digest.update(f"{rel}\0{file_hash}\n".encode())
    return digest.hexdigest()


def manifest_at(commit: str, path: str) -> dict:
    return tomllib.loads(git("show", f"{commit}:{path}/webcli-tool.toml"))


def load_index() -> dict:
    return json.loads(INDEX.read_text(encoding="utf-8"))


def check_index() -> list[str]:
    """index.json: the right shape, and each entry pinned to a commit in this branch's history whose files and
    manifest match it."""
    try:
        index = load_index()
    except (OSError, ValueError) as exc:
        return [f"index.json: can't read it: {exc}"]
    problems = []
    if index.get("repo") != REPO or index.get("archive") != ARCHIVE:
        problems.append(f'index.json: "repo" must be {REPO} and "archive" {ARCHIVE}')
    tools, revoked = index.get("tools"), index.get("revoked")
    if not isinstance(tools, list) or not isinstance(revoked, list):
        return problems + ['index.json: needs a "tools" list and a "revoked" list']
    for item in revoked:
        ok = isinstance(item, str) or (isinstance(item, dict) and isinstance(item.get("name"), str)
                                       and set(item) <= {"name", "versions", "reason"}
                                       and isinstance(item.get("versions", []), list)
                                       and all(isinstance(v, str) for v in item.get("versions", []))
                                       and isinstance(item.get("reason", ""), str))
        if not ok:
            problems.append(f'index.json revoked: {item!r} must be a name or {{"name", "versions", "reason"}}')
    names = [t.get("name") for t in tools if isinstance(t, dict)]
    problems += [f"index.json: {n!r} is listed twice" for n in sorted({n for n in names if names.count(n) > 1})]
    for entry in tools:
        where = f"index.json tool {entry.get('name') if isinstance(entry, dict) else entry!r}"
        if not isinstance(entry, dict) or set(entry) != ENTRY_KEYS:
            problems.append(f"{where}: needs exactly {', '.join(sorted(ENTRY_KEYS))}")
            continue
        name, commit = entry["name"], entry["commit"]
        shape = {"name": isinstance(name, str) and NAME.fullmatch(name),
                 "version": isinstance(entry["version"], str) and VERSION.fullmatch(entry["version"]),
                 "commit": isinstance(commit, str) and HEX40.fullmatch(commit),
                 "sha256": isinstance(entry["sha256"], str) and HEX64.fullmatch(entry["sha256"]),
                 "path": entry["path"] == f"tools/{name}",
                 "tier": entry["tier"] == "community",
                 "verified": isinstance(entry["verified"], bool),
                 "summary": isinstance(entry["summary"], str)}
        wrong = [key for key, ok in shape.items() if not ok]
        if wrong:
            problems.append(f"{where}: bad {', '.join(wrong)} (path is tools/<name>, tier is \"community\")")
            continue
        if subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", commit, "HEAD"],
                          capture_output=True).returncode != 0:
            problems.append(f"{where}: commit {commit[:12]} isn't in this branch's history")
            continue
        try:
            manifest = manifest_at(commit, entry["path"])
            got = tree_sha256(commit, entry["path"])
        except (subprocess.CalledProcessError, ValueError, tomllib.TOMLDecodeError) as exc:
            problems.append(f"{where}: can't read {entry['path']} at {commit[:12]}: {exc}")
            continue
        for key in ("name", "version", "summary"):
            if manifest.get(key) != entry[key]:
                problems.append(f"{where}: {key} is {entry[key]!r}, but the manifest at {commit[:12]} says "
                                f"{manifest.get(key)!r}")
        if got != entry["sha256"]:
            problems.append(f"{where}: sha256 doesn't match {entry['path']} at {commit[:12]} (it is {got}); "
                            f"run `python scripts/library.py pin {name} {commit}`")
    return problems


def tool_folders() -> list[Path]:
    return [ROOT / "TEMPLATE"] + sorted(p for p in (ROOT / "tools").iterdir() if p.is_dir())


def same_hash_as_webcli() -> list[str]:
    """webcli's own tree_sha256 (when this webcli has it) agrees with tree_sha256() on every tool at HEAD. Only on
    a clean checkout (CI), before anything writes into the tool folders."""
    if not os.environ.get("CI") or importlib.util.find_spec("webcli.core.index_client") is None:
        return []
    from webcli.core.index_client import tree_sha256 as webcli_tree_sha256

    return [f"{folder.relative_to(ROOT)}: webcli's tree_sha256 disagrees with scripts/library.py's; fix the script"
            for folder in tool_folders()[1:]
            if webcli_tree_sha256(folder) != tree_sha256("HEAD", folder.relative_to(ROOT).as_posix())]


def check_tool(folder: Path) -> list[str]:
    """`webcli lint` and `webcli test` (the network blocked), then plain pytest when it's installed."""
    rel = folder.relative_to(ROOT).as_posix()
    problems = []
    try:
        manifest = tomllib.loads((folder / "webcli-tool.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        manifest = {}
        problems.append(f"{rel}: can't read webcli-tool.toml: {exc}")
    if rel.startswith("tools/") and manifest and manifest.get("name") != folder.name:
        problems.append(f"{rel}: its manifest's name is {manifest.get('name')!r}; the folder must be "
                        f"tools/<name>")
    writes = [c.get("name") for c in manifest.get("commands", []) if isinstance(c, dict) and c.get("writes")]
    print(f"== {rel}: {manifest.get('name')} {manifest.get('version')}, "
          f"{'writes: ' + ', '.join(map(str, writes)) if writes else 'read-only'}", flush=True)
    for step in (["webcli", "lint", str(folder), "--format", "table"], ["webcli", "test", str(folder), "--format", "table"]):
        if subprocess.run(step).returncode != 0:
            problems.append(f"{rel}: `{' '.join(step[:2])}` failed (its output is above)")
    if importlib.util.find_spec("pytest") is not None:
        if subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=folder).returncode:
            problems.append(f"{rel}: pytest failed (its output is above)")
    return problems


def check_secrets() -> list[str]:
    """Every file in the repo, with the secret patterns `webcli lint` uses (it already scanned the tool folders,
    fixtures included, more strictly)."""
    from webcli.scaffold.checks import secrets

    return [f["message"] for f in secrets(ROOT) if f["level"] == "error"]


def check() -> int:
    if shutil.which("webcli") is None:
        print("webcli isn't on PATH: pip install --pre 'truefrontier-webcli>=1.0.0rc1'", file=sys.stderr)
        return 2
    problems = check_index() + same_hash_as_webcli()
    for folder in tool_folders():
        problems += check_tool(folder)
    problems += check_secrets()
    if problems:
        print(f"\n{len(problems)} problem(s):", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print(f"\nok: index.json, {len(tool_folders())} tool folders, secrets")
    return 0


def pin(name: str, commit: str = "HEAD") -> int:
    commit = git("rev-parse", f"{commit}^{{commit}}").strip()
    path = f"tools/{name}"
    manifest = manifest_at(commit, path)
    if manifest.get("name") != name:
        print(f"{path}/webcli-tool.toml at {commit[:12]} is named {manifest.get('name')!r}", file=sys.stderr)
        return 1
    index = load_index()
    old = next((t for t in index["tools"] if t["name"] == name), None)
    entry = {"name": name, "version": manifest["version"], "summary": manifest["summary"], "commit": commit,
             "sha256": tree_sha256(commit, path), "path": path, "tier": "community",
             "verified": bool(old and old["verified"] and old["version"] == manifest["version"])}
    index["tools"] = sorted([t for t in index["tools"] if t["name"] != name] + [entry], key=lambda t: t["name"])
    INDEX.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    print(f"pinned {name} {entry['version']} at {commit[:12]} (sha256 {entry['sha256'][:16]}...)")
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["check"] and len(argv) == 1:
        return check()
    if argv[:1] == ["pin"] and len(argv) in (2, 3):
        return pin(*argv[1:])
    print(__doc__.split("\n\n")[1], file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
