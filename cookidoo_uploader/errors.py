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


class LoginError(CookidooError):
    """Base class for credential-based auto-login failures."""


class BadCredentialsError(LoginError):
    """Raised when the CIAM IdP rejects the supplied email/password."""


class MFARequiredError(LoginError):
    """Raised when an MFA or interactive step-up page is detected.

    The HTTP login flow cannot complete MFA challenges.  Use the browser-cookie
    method instead (``cookidoo cookie --export``).
    """


class LoginFlowChangedError(LoginError):
    """Raised when the login HTML no longer contains the expected ``requestId``.

    This indicates the CIAM login page structure has changed and the scraping
    logic needs to be updated.  Use ``cookidoo cookie --export`` as a
    workaround in the meantime.
    """
