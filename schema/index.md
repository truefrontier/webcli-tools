# index.json

`index.json` is the library's list of tools. `webcli tools` downloads it, installs each community tool from the exact commit it names, and checks the files against the hash it names. It also carries the list of revoked tools, which webcli refuses to run.

It lists two kinds of tool:

- **Community tools** live in `tools/<name>/`. Each entry pins the tool to a commit and a hash.
- **Official built-ins** ship inside webcli, so they don't live here and never install from here. Their entries are a catalog: they let `webcli tools search` and `webcli tools info` show them next to the community tools. `webcli tools install` on one says it's already built in.

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
    },
    {
      "name": "loom",
      "version": "1.0.0rc1",
      "summary": "Loom, read-only: list, info, transcript (official transcripts), status (loom-cli parity)",
      "tier": "official",
      "builtin": true,
      "verified": true,
      "requires_webcli": ">=1.0.0rc1,<2",
      "source": "core",
      "identity": "loom",
      "hosts": [],
      "commands": [
        {"name": "list", "strategy": "cookie", "writes": false},
        {"name": "transcript", "strategy": "intercept", "writes": false}
      ],
      "docs": "https://github.com/truefrontier/webcli/blob/main/docs/social-data-sites.md"
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
| `tools` | One entry per tool, each name once, sorted by name. |
| `revoked` | Tools webcli refuses to run. See [Revoking a tool](#revoking-a-tool). |

### A community tool

| Field | Rule |
|---|---|
| `name` | The tool's name, as in its manifest. Not a name webcli keeps for itself: one of its commands, a built-in site, or the provider a built-in signs in as (`feed`, `gmail`, `google`, `none`). webcli won't load a tool by such a name. |
| `version` | The manifest's `version` at `commit`. |
| `summary` | The manifest's `summary` at `commit`. `webcli tools search` shows it. |
| `commit` | The full 40-character commit the tool installs from. Never a branch or a tag. It must be in `main`'s history. |
| `sha256` | The hash of the tool's files at `commit` (below). Install fails if the download doesn't match. |
| `path` | `tools/<name>`. |
| `tier` | `community`. |
| `verified` | `false`. Only a maintainer sets it `true`, and none does yet. A re-pin keeps `true` only when `sha256` is unchanged. |

`python scripts/library.py pin <name>` writes an entry, and CI checks every entry on every push.

### An official built-in

`builtin: true` with `tier: "official"` marks one. It has no `commit`, `sha256`, or `path`, because nothing installs from it.

| Field | Rule |
|---|---|
| `name` | The site's name in webcli. |
| `version` | The webcli release that ships it. |
| `summary` | The site's `summary` in that release. |
| `tier` | `official`. |
| `builtin` | `true`. |
| `verified` | `true`. |
| `requires_webcli` | The webcli versions that ship it, like `>=1.0.0rc1,<2`. |
| `source` | `core`. |
| `identity` | The provider it signs in with (`google`, `loom`), or `none` for a site that never signs in. |
| `hosts` | The site's declared hosts. Built-ins keep their own host policy in webcli, so today it's `[]`. |
| `commands` | One `{"name", "strategy", "writes"}` per command. `strategy` is `public`, `cookie`, `intercept`, or `ui`. `writes` is `true` only if the site declares that command as one that writes. |
| `docs` | Optional. A page in webcli's `docs/` folder about the site. |

Only webcli's **data** sites are listed. Its `llm` sites (`chatgpt`, `gemini`, and `muse`) belong to `llmcli`, not to this library of webcli data sites, so they aren't.

Don't write these entries by hand. From a webcli checkout at the release, run:

```
python scripts/library.py builtins
```

It reads every official data site from the webcli it imports and rewrites their entries. It leaves community entries alone, and it refuses if a community entry uses a built-in's name. Run it after each webcli release. CI checks the entries' shape, and that the webcli it installs can read the index.

## The hash

For each file in the tool's folder at that commit, take its path relative to the folder (with `/` between parts) and the SHA-256 of its bytes. Sort by path. The hash is the SHA-256 of all the lines `<path>\0<file sha256>\n`, joined. A tool holds regular files only: a link fails the check.

webcli computes the same thing as `tree_sha256` in `webcli/core/index_client.py`. CI checks that the two agree.

## Revoking a tool

An entry in `revoked` is a tool name, which revokes every version, or an object:

```json
{"name": "sometool", "versions": ["0.1.0"], "reason": "posted without asking"}
```

`versions` lists exact versions. Ranges aren't supported. webcli won't load a revoked tool, and a running webcli daemon re-reads the list before each of the tool's operations. A revoked tool keeps its `tools` entry only if a newer version is safe; otherwise remove the entry too.
