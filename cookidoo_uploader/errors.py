"""Shared error type and the actionable auth-failure hint."""

COOKIE_HINT = (
    "Cookie appears expired (server returned a login redirect / non-JSON, "
    "or 401/403). Log out and back in to Cookidoo and refresh COOKIDOO_COOKIE, "
    "or re-run `cookidoo cookie`."
)


class CookidooError(Exception):
    """Raised for any expected, user-actionable failure (auth, API, validation).

    The CLI catches this, prints the message to stderr, and exits non-zero —
    so library code never calls sys.exit() itself and stays testable.
    """
