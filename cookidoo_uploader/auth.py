"""Resolve the `_oauth2_proxy` session cookie from the env or the browser."""

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
    """Return (value, browser_name, domain) for the first match found, else None.

    browser_cookie3 is imported lazily so the package (and its tests) load
    without it — it's only needed for the browser-reading path.
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
    """Return the cookie value from $COOKIDOO_COOKIE, else from the browser.

    Raises CookidooError if neither source yields a cookie.
    """
    val = os.getenv("COOKIDOO_COOKIE")
    if val:
        return val
    res = find_cookie()
    if not res:
        raise CookidooError(
            "No Cookidoo cookie found. Set $COOKIDOO_COOKIE or log in to "
            "Cookidoo in a supported browser and re-run `cookidoo cookie`.")
    return res[0]
