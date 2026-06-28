# Design Plan: Credential-Based Automatic Login

**Status:** Design only — not yet implemented.
**Goal:** Let users store Cookidoo credentials (email + password) in config/env so the
tool logs in and obtains the `_oauth2_proxy` session cookie itself, instead of relying
on browser-cookie extraction or a manually pasted `$COOKIDOO_COOKIE`.

## Current state

`cookidoo_uploader/auth.py:get_cookie()` resolves the cookie from `$COOKIDOO_COOKIE`,
else scrapes it from installed browsers via `browser_cookie3`. The single contract to
preserve: **something must return a valid `_oauth2_proxy` cookie string.** Everything
below feeds that one function.

## Auth-flow research

Cookidoo runs **oauth2-proxy** in front of Vorwerk's **CIAM** identity provider. The
unofficial [`miaucl/cookidoo-api`](https://github.com/miaucl/cookidoo-api) proves a
**pure-`requests` login** that ends with the `_oauth2_proxy` + `v-authenticated` cookies:

1. `GET {domain}/profile/{lang}/login?redirectAfterLogin=...` (follow redirects) → CIAM login HTML.
2. Scrape the hidden `requestId` token from that HTML.
3. `POST https://ciam.prod.cookidoo.vorwerk-digital.com/login-srv/login` with
   `{requestId, username=<email>, password}` (follow redirects).
4. The redirect chain lands back on the cookidoo domain; the jar now holds
   `_oauth2_proxy`. Validate by asserting `{_oauth2_proxy, v-authenticated}` are present.

The OIDC `client_id`/`scope`/token dance is handled **inside oauth2-proxy**, so our client
never needs a client_id or a token endpoint — much simpler than a generic OIDC integration.

### Options

| Option | Feasible? | Deps | Fragility |
| --- | --- | --- | --- |
| **(b) Direct HTTP replay (recommended)** | Yes — proven by `cookidoo-api` | **none** (reuse `requests`) | Medium: breaks on CIAM markup change / CAPTCHA / MFA |
| (a) Headless browser (Playwright/Selenium) | Yes, most robust | Heavy (~100s of MB) | Lower for page changes; still dies on CAPTCHA/MFA; CI-unfriendly |
| (c) Reuse `cookidoo-api` | Yes | Adds `aiohttp`/async into a sync codebase | Inherits upstream breakage |
| (d) OIDC ROPC password grant | **Deprecated/broken** upstream | — | Do not build on this |

**Recommendation:** implement **(b)** as primary, keep **browser extraction as fallback**,
treat headless browser as an opt-in extra only if (b) proves fragile.

*Unconfirmed:* exact `requestId` field name and form body come from `cookidoo-api` source
and may drift; MFA/CAPTCHA enforcement is region/account dependent. Build assuming they can
appear and fail soft.

## Config design

- **Format:** TOML (`tomllib` is stdlib on 3.11+). **Location:** `~/.config/cookidoo/config.toml`
  (honor `$XDG_CONFIG_HOME`); optional project `./.cookidoo.toml` (gitignored); `--config` override.

```toml
[auth]
email = "you@example.com"
# password optional — prefer keyring/env/prompt (see Security)
password_keyring = true

[cookidoo]
domain = "https://cookidoo.co.uk"   # COOKIDOO_DOMAIN
locale = "en-GB"                     # COOKIDOO_LOCALE
tool   = "TM6"
```

**Cookie resolution order** (high→low): `--cookie` flag → `$COOKIDOO_COOKIE` → cached cookie
→ auto-login (then cache) → browser extraction → error.
**Credential order:** CLI/`getpass` prompt → env (`COOKIDOO_EMAIL`/`COOKIDOO_PASSWORD`) →
keyring → config file.

Refactor `get_cookie()` into this ordered chain so credentialed users get the smooth path
while cookie-only users see **zero behavior change**. Keep endpoint constants in `config.py`;
add user-config parsing in a new `userconfig.py` to avoid confusing the two "configs".

## Security (critical)

A stored password grants **full account access** over a private API. Treat it as a primary credential.

- **Primary store: OS keychain via `keyring`** (service `cookidoo-uploader`, username=email).
  `cookidoo login --set-password` stashes it with `getpass`, never echoed, never written to disk.
- **If plaintext config password is used (discouraged):** refuse/warn unless file is `0600`;
  dir `0700`; gitignore the config.
- **Never log the password or cookie**; scrub from verbose output and exception messages
  (never dump the login POST body).
- **Interactive `getpass` prompt** as a first-class option (store nothing on disk).
- **Cookie caching:** after login, cache `_oauth2_proxy` + expiry to `~/.config/cookidoo/cookie.json`
  mode `0600`; on `401/403` invalidate and re-login once. Minimizes login frequency.

## Implementation sketch

New `cookidoo_uploader/login.py`:

```python
def login(email, password, *, domain, locale, session=None) -> str:
    """GET login page → scrape requestId → POST creds → return _oauth2_proxy.
    Raises BadCredentialsError / MFARequiredError / LoginFlowChangedError."""

def get_cookie_via_login() -> str | None:
    """Resolve creds (keyring/env/prompt/config), call login(), cache.
    Returns None when no creds configured so callers fall through to browser."""
```

**Failure taxonomy:** no creds → return `None` (fall through); bad creds → `BadCredentialsError`;
MFA/CAPTCHA/step-up → `MFARequiredError` ("use the browser-cookie method"); `requestId` missing →
`LoginFlowChangedError`. Degrade to browser/manual rather than hard-fail.

**New deps:** none for HTTP login; `keyring` (optional, lazy-imported like `browser_cookie3`);
regex (not bs4) for `requestId`; `tomllib`/`tomli`. **Do not** add Playwright/Selenium by default —
gate behind a `[browser]` extra if ever needed.

**Phases:** (1) HTTP login + config/env/prompt creds + `0600` cookie cache, no new hard deps;
(2) `keyring` + `login --set-password`/`--set-email` + permission hardening; (3) optional headless fallback.

**Tests without real creds:** mock the IdP with `responses`/`requests_mock` — stub the login GET to
return HTML with a known `requestId`, stub the CIAM POST to set `Set-Cookie: _oauth2_proxy=...`;
assert `login()` returns it. Negative: no auth cookie → bad creds; missing `requestId` → flow-changed;
interstitial page → MFA. Precedence/cache/security tests as above.

## Risks & open questions

1. **MFA/2FA** — HTTP password flow can't complete; detect and fall back to browser.
2. **CAPTCHA / bot protection / lockout** — cache aggressively; never hammer on failure.
3. **ToS/legal** — automating login against a private endpoint likely contravenes Vorwerk's
   Terms; keep credentials **opt-in** and documented; consider document-only.
4. **Upstream fragility** — `requestId` scrape + form body are unversioned; isolate in `login.py`,
   fail soft, track `cookidoo-api` for breakage.
5. **Dependency weight** — `keyring` optional = yes; default headless automation = no.
6. **Plaintext policy** — allow with `0600` enforcement but loudly discourage; default docs to keyring/prompt.
7. **Cookie-expiry signal** — confirm Set-Cookie carries usable expiry; else conservative TTL + 401-retry.
8. **Region coverage** — confirm the single `ciam.prod...vorwerk-digital.com` host serves all locales.

## References

- [miaucl/cookidoo-api](https://github.com/miaucl/cookidoo-api) — proven CIAM login yielding `_oauth2_proxy`
- [cookidoo-api issue #26](https://github.com/miaucl/cookidoo-api/issues/26) — deprecated ROPC token flow
- [oauth2-proxy](https://github.com/oauth2-proxy/oauth2-proxy) — the proxy fronting Cookidoo
