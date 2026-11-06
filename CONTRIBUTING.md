# Contributing a tool

A tool here gives webcli users commands for one website. You build it with `webcli new`, check it with `webcli lint` and `webcli test`, and send it with `webcli submit`. A maintainer reviews it, merges it, and pins it in `index.json`. Then anyone can install it.

## Before you start

- **Use your own account, within the site's terms.** Read the [README](README.md#use-tools-within-the-sites-terms). Don't submit a tool for a site whose terms forbid it.
- **One tool per site.** Search first (`webcli tools search`). If a tool for the site exists, improve it instead.
- **Read-only first.** Start with commands that only read. A tool that writes gets a much closer review.

## Build it

```
webcli new acmenotes --url https://notes.example.com/   # add --capture to record what the site loads
webcli dev acmenotes -- page
webcli lint acmenotes
webcli test acmenotes
```

webcli's [making-a-tool guide](https://github.com/truefrontier/webcli/blob/main/docs/making-a-tool.md) covers each step. [`TEMPLATE/`](TEMPLATE/) shows what `webcli new` makes, and [`tools/httpbin/`](tools/httpbin/) is a finished example.

## The rules

CI checks every rule it can. Reviewers check the rest.

| Rule | Checked by |
|---|---|
| The manifest is valid, and the tool's `ADAPTER` agrees with it. | CI (`webcli lint`) |
| The name is 2 to 32 lowercase letters and digits, with no hyphens. The folder is `tools/<name>/`. | CI |
| `hosts` lists every host the tool reaches, and the tool's guard refuses every other host. | CI checks the guard; reviewers check the list is complete |
| Read-only by default. A command that changes anything is marked `writes = true`, takes `--confirm`, and is a dry run without it. A read-only tool's guard refuses PUT, PATCH, and DELETE. | CI (`webcli lint`); reviewers read every write |
| A command that messages, posts, or invites someone is also marked `sends_to_people = true`. | Reviewers |
| The tool signs in as its own identity (`identity` defaults to the tool's name). If it needs another provider's sign-in, say why in the pull request. | Reviewers |
| The tool imports only `webcli.adapter` from webcli. | CI |
| Offline tests in `tests/test_*.py` pass with the network blocked. | CI (`webcli test` and pytest) |
| No secrets anywhere: no cookies, tokens, API keys, or `Authorization` values. | CI scans every file |
| Fixtures (`tests/fixtures/`) hold no one's personal details: no real names, email addresses, phone numbers, messages, or account IDs. Replace them with made-up ones. | CI catches tokens and emails; reviewers read every fixture |
| `maintainers` lists your GitHub login, and you'll fix the tool when the site changes. | Reviewers |
| No code that hides what it does: no downloading and running code, no obfuscation, no reaching outside the tool's hosts by other means. | Reviewers |

## Send it

```
webcli submit acmenotes            # runs lint and the tests, shows the checklist and the plan; sends nothing
webcli submit acmenotes --confirm  # asks the checklist, then forks this repo and opens the pull request
```

`--confirm` needs the [GitHub CLI](https://cli.github.com/), signed in (`gh auth login`). It copies your tool into `tools/<name>/` on a new branch of your fork and opens a pull request here. It leaves out hidden files and caches.

You can also open the pull request by hand: put the tool in `tools/<name>/` and run `python scripts/library.py check` first. Don't edit `index.json` in your pull request.

## Review

A maintainer reads the code, the manifest, and every fixture. They may ask for changes. A tool that writes, or that asks for another provider's sign-in, needs a clear reason. CI must pass before merge.

## After the merge

A maintainer pins the tool so `webcli tools install` can find it:

```
git pull
python scripts/library.py pin acmenotes      # pins tools/acmenotes at HEAD in index.json
git commit -am "Pin acmenotes 0.1.0" && git push
```

The pin names the commit and the hash of the tool's files. Until it's pinned, the tool isn't installable.

## Updating a tool

Change the files, raise `version` in both `webcli-tool.toml` and `ADAPTER`, and submit again. If the update adds hosts, write commands, or a different identity, say so in the pull request: `webcli tools update` stops and asks each user before it installs a change like that.

## Revoking a tool

A maintainer adds the tool to `revoked` in `index.json` ([format](schema/index.md#revoking-a-tool)). Any user, including a site owner, can ask for that with a [takedown request](README.md#takedown-requests).
