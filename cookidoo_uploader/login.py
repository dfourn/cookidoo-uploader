"""Pure-requests CIAM login yielding the ``_oauth2_proxy`` session cookie.

WARNING: This login flow is reverse-engineered from the miaucl/cookidoo-api
project (https://github.com/miaucl/cookidoo-api) and has NOT been verified
against the live Cookidoo/Vorwerk CIAM endpoint.  The ``requestId`` field name
and POST body structure may change without notice.  MFA and CAPTCHA enforcement
may block this flow entirely for some accounts or regions.

Do not call this with real credentials from automated tests — inject a ``session``
instead (see :func:`login`).
"""

import re
from typing import Optional

import requests

from .config import DOMAIN, LOCALE
from .errors import BadCredentialsError, LoginFlowChangedError, MFARequiredError

CIAM_LOGIN_URL = "https://ciam.prod.cookidoo.vorwerk-digital.com/login-srv/login"

# Matches:  name="requestId" value="<token>"  or  name='requestId' value='<token>'
_REQUEST_ID_RE = re.compile(
    r'name=["\']requestId["\']\s+value=["\']([\w-]+)["\']'
    r'|value=["\']([\w-]+)["\']\s+name=["\']requestId["\']'
)


def _lang_from_locale(locale: str) -> str:
    """Derive the two-letter language prefix from a locale tag (``en-GB`` → ``en``)."""
    return locale.split("-")[0].lower()


def login(
    email: str,
    password: str,
    *,
    domain: str = DOMAIN,
    locale: str = LOCALE,
    session: Optional[requests.Session] = None,
) -> str:
    """Perform the Cookidoo CIAM HTTP login and return the ``_oauth2_proxy`` value.

    Steps (reverse-engineered — unverified against the live API):

    1. ``GET {domain}/profile/{lang}/login?redirectAfterLogin=...`` — follows
       redirects to the CIAM login HTML page.
    2. Scrape the hidden ``requestId`` form field from the HTML using a regex.
    3. ``POST`` ``{requestId, username=email, password}`` to the CIAM endpoint —
       follows redirects back to the Cookidoo domain, setting session cookies.
    4. Assert ``_oauth2_proxy`` is in the session cookie jar.

    Pass ``session`` to inject a fake session for testing; a real
    :class:`requests.Session` is created when omitted.

    Raises:
        :class:`~cookidoo_uploader.errors.LoginFlowChangedError`:
            ``requestId`` not found in the login HTML.
        :class:`~cookidoo_uploader.errors.BadCredentialsError`:
            No auth cookies after the POST (likely wrong email/password).
        :class:`~cookidoo_uploader.errors.MFARequiredError`:
            ``v-authenticated`` present but ``_oauth2_proxy`` absent —
            an MFA or step-up interstitial was returned.
    """
    s = session if session is not None else requests.Session()

    lang = _lang_from_locale(locale)
    redirect_target = f"{domain}/created-recipes/{locale}"
    login_page_url = f"{domain}/profile/{lang}/login"

    # Step 1: GET the login page (follow redirects to CIAM login HTML).
    resp = s.get(login_page_url, params={"redirectAfterLogin": redirect_target})
    html = resp.text

    # Step 2: scrape requestId — do NOT log the HTML (it may contain token hints).
    m = _REQUEST_ID_RE.search(html)
    if not m:
        raise LoginFlowChangedError(
            "Could not find 'requestId' in the Cookidoo login page. "
            "The CIAM login page structure may have changed. "
            "Use `cookidoo cookie --export` (browser extraction) as a workaround "
            "and report this issue."
        )
    request_id = m.group(1) or m.group(2)

    # Step 3: POST credentials.  NEVER log the form body.
    form_data = {
        "requestId": request_id,
        "username": email,
        "password": password,
    }
    s.post(CIAM_LOGIN_URL, data=form_data)

    # Step 4: inspect the session cookie jar.
    jar_names = {c.name for c in s.cookies}

    if "_oauth2_proxy" not in jar_names:
        if "v-authenticated" in jar_names:
            # Step-up / MFA interstitial: some auth happened but the proxy
            # cookie was not issued.
            raise MFARequiredError(
                "Login returned an MFA or step-up challenge that the automatic "
                "login flow cannot complete. "
                "Use `cookidoo cookie --export` (browser extraction) instead."
            )
        # Neither cookie — most likely wrong credentials.
        raise BadCredentialsError(
            "Login failed: the session did not receive the expected auth cookies "
            "after submitting credentials. Check your email and password. "
            "If your account requires MFA or the request was blocked by CAPTCHA, "
            "use `cookidoo cookie --export` (browser extraction) instead."
        )

    # Retrieve value and optional expiry from the cookie jar.
    oauth_cookie = next(c for c in s.cookies if c.name == "_oauth2_proxy")
    value: str = oauth_cookie.value
    return value


def get_cookie_via_login() -> Optional[str]:
    """Attempt credential-based login; return the cookie or ``None`` if not configured.

    Resolves credentials via :mod:`cookidoo_uploader.userconfig` (env vars,
    keyring, config file, or interactive prompt).  Returns ``None`` — and does
    NOT raise — when no credentials are configured, so the caller can fall
    through to the browser-extraction path.

    On success the cookie is written to the disk cache for future runs.
    Never logs or prints the password or cookie value.

    Raises:
        :class:`~cookidoo_uploader.errors.BadCredentialsError`:
            Credentials are configured but the IdP rejected them.
        :class:`~cookidoo_uploader.errors.MFARequiredError`:
            An MFA / step-up challenge was detected.
        :class:`~cookidoo_uploader.errors.LoginFlowChangedError`:
            The login page structure has changed.
    """
    # Deferred import: avoids loading tomllib/userconfig unless the login path
    # is actually taken.
    from .userconfig import load_config, resolve_email, resolve_password

    config = load_config()

    email = resolve_email(config=config)
    if not email:
        return None  # no email configured — fall through to browser path

    password = resolve_password(email, config=config)
    if not password:
        return None  # no password and no TTY prompt — fall through

    domain: str = config.get("cookidoo", {}).get("domain", DOMAIN)
    locale: str = config.get("cookidoo", {}).get("locale", LOCALE)

    value = login(email, password, domain=domain, locale=locale)

    # Cache the cookie for future runs (best-effort; ignore write errors).
    try:
        from .cache import write_cached_cookie
        write_cached_cookie(value)
    except Exception:
        pass

    return value
