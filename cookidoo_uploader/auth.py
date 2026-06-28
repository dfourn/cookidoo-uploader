"""Resolve the ``_oauth2_proxy`` session cookie.

Resolution order:
  1. ``$COOKIDOO_COOKIE`` environment variable  (existing behaviour, unchanged)
  2. Disk cache from a previous auto-login
  3. Credential-based auto-login (then cached for future runs)
  4. Browser cookie extraction via ``browser_cookie3``
  5. :class:`~cookidoo_uploader.errors.CookidooError` is raised

All imports for optional dependencies (keyring, browser_cookie3, tomllib) are
deferred so the package stays importable without them installed.
"""

import os

from .errors import CookidooError

COOKIE_NAME = "_oauth2_proxy"

# Cookidoo runs on region-specific domains; check the common ones.
DOMAINS = [
    "cookidoo.de",
    "cookidoo.co.uk",
    "cookidoo.thermomix.com",
    "cookidoo.com",
    "cookidoo.international",
]


def find_cookie():
    """Return ``(value, browser_name, domain)`` for the first match found, else ``None``.

    ``browser_cookie3`` is imported lazily so the package (and its tests) load
    without it — it is only needed for the browser-reading path.
    """
    import browser_cookie3

    browsers = [
        (browser_cookie3.chrome, "Chrome"),
        (browser_cookie3.safari, "Safari"),
        (browser_cookie3.firefox, "Firefox"),
        (browser_cookie3.edge, "Edge"),
        (browser_cookie3.brave, "Brave"),
    ]
    for loader, name in browsers:
        for domain in DOMAINS:
            try:
                jar = loader(domain_name=domain)
            except Exception:
                # Browser not installed / locked / no keychain access — skip.
                continue
            for c in jar:
                if c.name == COOKIE_NAME and c.value:
                    return c.value, name, c.domain
    return None


def get_cookie() -> str:
    """Return the ``_oauth2_proxy`` cookie value.

    Tries each source in the resolution order documented in the module
    docstring.  Raises :class:`~cookidoo_uploader.errors.CookidooError` only
    after all sources are exhausted.

    :class:`~cookidoo_uploader.errors.LoginError` subclasses (bad credentials,
    MFA required, flow changed) propagate directly to the caller — they carry
    actionable messages and should not be silently swallowed.
    """
    # 1. Explicit env override — existing behaviour, highest priority.
    val = os.getenv("COOKIDOO_COOKIE")
    if val:
        return val

    # 2. Disk cache from a previous successful login.
    try:
        from .cache import read_cached_cookie
        cached = read_cached_cookie()
        if cached:
            return cached
    except Exception:
        pass

    # 3. Credential-based auto-login.  LoginError subclasses propagate; only
    #    ImportError (login module unavailable) is swallowed.
    try:
        from .login import get_cookie_via_login
    except ImportError:
        pass
    else:
        auto = get_cookie_via_login()
        if auto:
            return auto

    # 4. Browser cookie extraction.
    res = find_cookie()
    if res:
        return res[0]

    raise CookidooError(
        "No Cookidoo cookie found. Options:\n"
        "  • Set $COOKIDOO_COOKIE\n"
        "  • Configure credentials in ~/.config/cookidoo/config.toml "
        "and run `cookidoo login`\n"
        "  • Log in to Cookidoo in a supported browser and re-run "
        "`cookidoo cookie`"
    )
