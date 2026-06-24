#!/usr/bin/env python3
"""
Retrieve the Cookidoo `_oauth2_proxy` auth cookie directly from your browser.

Reads (and on macOS decrypts via Keychain) cookies from your installed
browsers and finds the Cookidoo session cookie, so you don't have to dig
through DevTools by hand.

Usage:
    cookiput_venv/bin/python scripts/get_cookidoo_cookie.py            # print it
    eval "$(cookiput_venv/bin/python scripts/get_cookidoo_cookie.py --export)"   # set $COOKIDOO_COOKIE in your shell

The first run may trigger a one-time Keychain prompt ("... wants to use your
confidential information stored in Chrome Safe Storage") — that's the OS
letting Python read the browser's cookie-encryption key. Click Allow.
"""

import argparse
import sys

import browser_cookie3

# Cookidoo runs on region-specific domains; check the common ones.
DOMAINS = [
    "cookidoo.de",
    "cookidoo.co.uk",
    "cookidoo.thermomix.com",
    "cookidoo.com",
    "cookidoo.international",
]

COOKIE_NAME = "_oauth2_proxy"

# (loader function, human-readable browser name)
BROWSERS = [
    (browser_cookie3.chrome, "Chrome"),
    (browser_cookie3.safari, "Safari"),
    (browser_cookie3.firefox, "Firefox"),
    (browser_cookie3.edge, "Edge"),
    (browser_cookie3.brave, "Brave"),
]


def find_cookie():
    """Return (value, browser_name, domain) for the first match found, else None."""
    for loader, name in BROWSERS:
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


def main():
    parser = argparse.ArgumentParser(description="Fetch the Cookidoo _oauth2_proxy cookie from your browser.")
    parser.add_argument("--export", action="store_true",
                        help="print a shell `export COOKIDOO_COOKIE=...` line instead of the raw value")
    args = parser.parse_args()

    result = find_cookie()
    if not result:
        print(
            "Could not find the Cookidoo `_oauth2_proxy` cookie in any browser.\n"
            "Make sure you are logged in to Cookidoo (e.g. https://cookidoo.de) in\n"
            "Chrome, Safari, Firefox, Edge, or Brave, then run this again.",
            file=sys.stderr,
        )
        sys.exit(1)

    value, browser, domain = result
    if args.export:
        # Single-quote the value so shell special chars are safe.
        print(f"export COOKIDOO_COOKIE='{value}'")
    else:
        print(f"Found `{COOKIE_NAME}` in {browser} (domain {domain}):\n", file=sys.stderr)
        print(value)


if __name__ == "__main__":
    main()
