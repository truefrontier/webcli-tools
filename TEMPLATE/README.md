> **This is the template.** It's what `webcli new` makes, with the name `yourtool` and the placeholder host `www.example.com`. Run `webcli new <name> --url <https://the-site/>` to get your own copy with the name and host filled in, rather than copying this folder by hand.

# webcli yourtool

A read-only [webcli](https://github.com/truefrontier/webcli) tool for www.example.com. It opens https://www.example.com/ in your own hidden Chrome, signed in as `yourtool:default`, and reads the page. It never changes anything on the site.

## Try it

```
webcli dev yourtool -- page        # the page's headings and links
webcli dev yourtool -- status      # can it read the site signed in?
webcli identity login yourtool:default   # sign in once, if the site needs it (a person does this)
```

## Make it yours

| File | What to change |
|---|---|
| `webcli_tool_yourtool/fetch.py` | What the tool reads off the page (`PAGE_JS`), or the site's own JSON API |
| `webcli_tool_yourtool/parse.py` | How that becomes rows. Keep it pure, so tests can check it offline |
| `webcli_tool_yourtool/cli.py` | The commands people type |
| `webcli_tool_yourtool/endpoints.py` and `webcli-tool.toml` | Every host the tool reaches. Keep the two lists the same |
| `tests/` | Tests that run offline, against the pages in `tests/fixtures/` |

A tool imports from `webcli.adapter` and its own package only. Each command you add goes in the manifest's `[[commands]]` too, and in `ADAPTER.verbs`. A command that changes something on the site needs `writes = true` in the manifest and `--confirm` to run; the library reviews every one.

## Check it

```
webcli lint yourtool    # the checks the library's CI runs
webcli test yourtool    # the tests, with the network blocked
```

## Share it

`webcli submit yourtool` opens a pull request to the [webcli-tools](https://github.com/truefrontier/webcli-tools) library. Before you do, read `tests/fixtures/`: it must not hold cookies, tokens, or anyone's personal details. Use the tool only with your own accounts and within the site's terms.
