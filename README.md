# webcli-tools

Community tools for [webcli](https://github.com/truefrontier/webcli). Each tool adds commands for one website, like `webcli httpbin ip`. Install them with `webcli tools install`, or share your own with `webcli submit`.

The tools here are written by people outside True Frontier. They're reviewed before they're merged, but they aren't endorsed. Read a tool's manifest before you install it.

## Use a tool

You need webcli 1.0 or later (`pip install --pre truefrontier-webcli` while 1.0 is a release candidate).

```
webcli tools search            # what's in the library
webcli tools info httpbin      # what it reads, what it writes, which identity it uses
webcli tools install httpbin   # shows the manifest and asks first
webcli httpbin ip
```

`webcli tools install` downloads the tool from the exact commit in [`index.json`](index.json) and checks its files against the hash there.

`webcli tools search` also lists webcli's official built-ins, like `loom` and `gmail`, marked `builtin`. They're already part of webcli, so `webcli tools install` on one has nothing to do.

## What webcli holds a community tool to

| Rule | What it means for you |
|---|---|
| Its own identity | A tool signs in as `<tool>:default`. It can't use one of your existing logins, like `google:default`, unless you run `webcli tools grant <tool> <identity>`. |
| Its own hosts | Its browser pages can reach only the hosts in its manifest. webcli blocks the rest. |
| Read-only by default | A command that changes anything on a site must say so in the manifest (`writes = true`). It runs as a dry run unless you pass `--confirm`. |
| No shadowing | A tool can't take the name of a built-in site or a webcli command. |
| A kill switch | A tool listed under `revoked` in `index.json` stops running everywhere webcli refreshes the index. |

These rules catch honest mistakes. They don't make a stranger's code safe: a tool is Python that runs as you, next to your signed-in sessions. Install only tools you've read, or tools from people you trust. A tool that calls a site without a browser (like `httpbin`) also has to keep to its hosts itself; reviewers check that.

## Use tools within the site's terms

- **Use your own accounts.** A tool works as you, in your own signed-in browser. Don't use one to reach accounts or data that aren't yours.
- **Follow the site's terms of service.** Many sites restrict automated access. Whether a tool's use is allowed is between you and the site. The library doesn't grant any rights to a site's service or data.
- **Personal use.** These tools are for reading your own data at a person's pace. Don't use them for scraping at scale, spam, or anything that would harm a site or its users.
- **You're responsible.** The tools come with no warranty (see [LICENSE](LICENSE)). Whoever runs a tool is responsible for what it does with their accounts.

## Takedown requests

If you run a site and want a tool for it removed, or you think a tool is harmful, [open an issue](https://github.com/truefrontier/webcli-tools/issues/new) titled `Takedown: <tool>`. Say which tool, and why. For anything sensitive, like a tool that leaks data, use **Security > Report a vulnerability** on this repository instead, so the report stays private.

A maintainer reviews each request. A harmful tool goes on the `revoked` list first, which stops it on every machine that refreshes the index, and then it's removed.

## Make a tool

```
webcli new acmenotes --url https://notes.example.com/
webcli lint acmenotes
webcli test acmenotes
webcli submit acmenotes          # a dry run: shows the checks and the pull request it would open
webcli submit acmenotes --confirm
```

[CONTRIBUTING.md](CONTRIBUTING.md) has the rules a tool must meet and how review works.

## What's here

| Path | What it is |
|---|---|
| `tools/<name>/` | One tool per folder. The folder's name is the tool's name. |
| `index.json` | The installable tools, each pinned to a commit and a hash; a catalog of webcli's official built-ins; and the revoked list ([format](schema/index.md)). |
| `TEMPLATE/` | What `webcli new` makes: a read-only tool that reads one page in your signed-in browser. |
| `schema/` | The manifest rules ([webcli-tool-manifest.md](schema/webcli-tool-manifest.md), a copy of webcli's) and the index format ([index.md](schema/index.md)). |
| `scripts/library.py` | The checks CI runs, and how maintainers pin a tool. |

## License

MIT. Each tool also states its own license in its manifest.
