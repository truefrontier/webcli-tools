# webcli httpbin

A read-only demo tool for [webcli](https://github.com/truefrontier/webcli). It calls [httpbin.org](https://httpbin.org), a public test service, over plain HTTPS. It needs no sign-in and no browser, and it never changes anything.

```
webcli tools install httpbin
webcli httpbin ip          # the public IP address httpbin.org sees
webcli httpbin headers     # the request headers it received
webcli httpbin uuid        # a random UUID
```

It's here to show the shape of a library tool and to give `webcli tools install` something safe to install. It sends every request to `httpbin.org` only, as GET, and it doesn't follow redirects. `webcli lint` and `webcli test` check it in the library's CI.

Note that `ip` shows your public IP address, and httpbin.org sees it on every request, as any website would.
