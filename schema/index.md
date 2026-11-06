# index.json

`index.json` is the library's list of tools. `webcli tools` downloads it, installs each tool from the exact commit it names, and checks the files against the hash it names. It also carries the list of revoked tools, which webcli refuses to run.

Only maintainers change it. A pull request that adds or updates a tool doesn't touch it: after the merge, a maintainer pins the tool (see [CONTRIBUTING.md](../CONTRIBUTING.md#after-the-merge)).

## Example

```json
{
  "repo": "https://github.com/truefrontier/webcli-tools",
  "archive": "https://codeload.github.com/truefrontier/webcli-tools/tar.gz/{commit}",
  "tools": [
    {
      "name": "httpbin",
      "version": "0.1.0",
      "summary": "httpbin.org, read-only demo: your public IP, the headers it sees, a fresh UUID. No sign-in, no browser",
      "commit": "0123456789abcdef0123456789abcdef01234567",
      "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "path": "tools/httpbin",
      "tier": "community",
      "verified": false
    }
  ],
  "revoked": [
    "sometool",
    {"name": "othertool", "versions": ["0.1.0"], "reason": "posted without asking"}
  ]
}
```

## Fields

| Field | Rule |
|---|---|
| `repo` | This repository's URL. |
| `archive` | Where to download a commit: a URL with `{commit}` in it. |
| `tools` | One entry per tool, each name once. |
| `revoked` | Tools webcli refuses to run. See [Revoking a tool](#revoking-a-tool). |

Each entry in `tools`:

| Field | Rule |
|---|---|
| `name` | The tool's name, as in its manifest. |
| `version` | The manifest's `version` at `commit`. |
| `summary` | The manifest's `summary` at `commit`. `webcli tools search` shows it. |
| `commit` | The full 40-character commit the tool installs from. Never a branch or a tag. It must be in `main`'s history. |
| `sha256` | The hash of the tool's files at `commit` (below). Install fails if the download doesn't match. |
| `path` | `tools/<name>`. |
| `tier` | Always `community`. Official tools ship inside webcli, not here. |
| `verified` | `false`. Only a maintainer sets it `true`, and none does yet. |

`python scripts/library.py pin <name>` writes an entry, and CI checks every entry on every push.

## The hash

For each file in the tool's folder at that commit, take its path relative to the folder (with `/` between parts) and the SHA-256 of its bytes. Sort by path. The hash is the SHA-256 of all the lines `<path>\0<file sha256>\n`, joined. A tool holds regular files only: a link fails the check.

webcli computes the same thing as `tree_sha256` in `webcli/core/index_client.py`. CI checks that the two agree.

## Revoking a tool

An entry in `revoked` is a tool name, which revokes every version, or an object:

```json
{"name": "sometool", "versions": ["0.1.0"], "reason": "posted without asking"}
```

`versions` lists exact versions. Ranges aren't supported. webcli won't load a revoked tool, and a running webcli daemon re-reads the list before each of the tool's operations. A revoked tool keeps its `tools` entry only if a newer version is safe; otherwise remove the entry too.
