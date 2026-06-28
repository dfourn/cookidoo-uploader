"""Tests for cookidoo_uploader.login and cookidoo_uploader.cache.

All tests use injected fake sessions — no real network, no real credentials.
"""

from datetime import datetime, timezone

import pytest

from cookidoo_uploader.errors import (
    BadCredentialsError,
    LoginFlowChangedError,
    MFARequiredError,
)
from cookidoo_uploader.login import CIAM_LOGIN_URL, login


# ---------------------------------------------------------------------------
# Fake HTTP primitives (mirror tests/test_client.py style)
# ---------------------------------------------------------------------------

class FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, status=200, text=""):
        self.status_code = status
        self.text = text

    @property
    def ok(self):
        return self.status_code < 400


class FakeCookie:
    """Minimal stand-in for a requests cookie jar entry."""

    def __init__(self, name, value, expires=None):
        self.name = name
        self.value = value
        self.expires = expires


class FakeCookieJar:
    """Iterable cookie jar pre-loaded with FakeCookie objects."""

    def __init__(self, cookies):
        self._cookies = list(cookies)

    def __iter__(self):
        return iter(self._cookies)


class FakeSession:
    """Records calls and returns queued responses; cookies are pre-injected."""

    def __init__(self, get_html, post_cookies=()):
        """
        *get_html*: HTML string returned by the GET login-page call.
        *post_cookies*: sequence of ``(name, value)`` or ``(name, value, expires)``
            tuples — placed in the session jar before the caller inspects it.
        """
        self._get_html = get_html
        self.cookies = FakeCookieJar(
            FakeCookie(*c) if len(c) == 3 else FakeCookie(c[0], c[1])
            for c in post_cookies
        )
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return FakeResponse(text=self._get_html)

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return FakeResponse()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LOGIN_HTML_TEMPLATE = """\
<html><body>
<input type="hidden" name="requestId" value="{rid}" />
</body></html>
"""

_HTML_WITH_RID = _LOGIN_HTML_TEMPLATE.format(rid="test-request-id-123")
_HTML_WITHOUT_RID = "<html><body><form></form></body></html>"


def _make_session(html=_HTML_WITH_RID, cookies=()):
    return FakeSession(get_html=html, post_cookies=cookies)


# ---------------------------------------------------------------------------
# login() — happy path
# ---------------------------------------------------------------------------

def test_login_returns_oauth2_proxy_value():
    sess = _make_session(
        cookies=[("_oauth2_proxy", "proxy-tok-abc"), ("v-authenticated", "true")],
    )
    result = login("user@example.com", "s3cr3t",
                   domain="https://cookidoo.co.uk", locale="en-GB",
                   session=sess)
    assert result == "proxy-tok-abc"


def test_login_makes_get_then_post():
    sess = _make_session(
        cookies=[("_oauth2_proxy", "tok"), ("v-authenticated", "1")],
    )
    login("u@e.com", "p", domain="https://cookidoo.co.uk", locale="en-GB", session=sess)
    methods = [m for m, _, _ in sess.calls]
    assert methods == ["GET", "POST"]


def test_login_get_includes_redirect_param():
    sess = _make_session(cookies=[("_oauth2_proxy", "tok")])
    login("u@e.com", "p", domain="https://cookidoo.co.uk", locale="en-GB", session=sess)
    _, get_url, get_kw = sess.calls[0]
    assert "cookidoo.co.uk" in get_url
    assert "redirectAfterLogin" in get_kw.get("params", {})


def test_login_post_targets_ciam_url():
    sess = _make_session(cookies=[("_oauth2_proxy", "tok")])
    login("u@e.com", "p", domain="https://cookidoo.co.uk", locale="en-GB", session=sess)
    _, post_url, _ = sess.calls[1]
    assert post_url == CIAM_LOGIN_URL


def test_login_post_sends_request_id():
    sess = _make_session(cookies=[("_oauth2_proxy", "tok")])
    login("u@e.com", "p", domain="https://cookidoo.co.uk", locale="en-GB", session=sess)
    _, _, post_kw = sess.calls[1]
    assert post_kw["data"]["requestId"] == "test-request-id-123"


def test_login_lang_derived_from_locale():
    """GET URL should use the language prefix, not the full locale."""
    sess = _make_session(cookies=[("_oauth2_proxy", "tok")])
    login("u@e.com", "p", domain="https://cookidoo.de", locale="de-DE", session=sess)
    _, get_url, _ = sess.calls[0]
    assert "/profile/de/login" in get_url


def test_login_alternative_attribute_order():
    """requestId regex should match when value= comes before name=."""
    html = '<input value="alt-rid-999" name="requestId" type="hidden" />'
    sess = _make_session(html=html, cookies=[("_oauth2_proxy", "tok")])
    result = login("u@e.com", "p", domain="https://cookidoo.co.uk", locale="en-GB",
                   session=sess)
    assert result == "tok"


# ---------------------------------------------------------------------------
# login() — negative paths
# ---------------------------------------------------------------------------

def test_login_missing_request_id_raises_flow_changed():
    sess = _make_session(html=_HTML_WITHOUT_RID)
    with pytest.raises(LoginFlowChangedError):
        login("u@e.com", "p", domain="https://cookidoo.co.uk", locale="en-GB",
              session=sess)


def test_login_no_auth_cookies_raises_bad_credentials():
    sess = _make_session(cookies=[])  # no cookies at all
    with pytest.raises(BadCredentialsError):
        login("u@e.com", "wrongpass",
              domain="https://cookidoo.co.uk", locale="en-GB", session=sess)


def test_login_mfa_interstitial_raises_mfa_required():
    # v-authenticated present but _oauth2_proxy absent → step-up challenge.
    sess = _make_session(cookies=[("v-authenticated", "true")])
    with pytest.raises(MFARequiredError):
        login("u@e.com", "p", domain="https://cookidoo.co.uk", locale="en-GB",
              session=sess)


def test_bad_credentials_error_message_mentions_browser_fallback():
    sess = _make_session(cookies=[])
    with pytest.raises(BadCredentialsError, match="browser extraction"):
        login("u@e.com", "bad", domain="https://cookidoo.co.uk", locale="en-GB",
              session=sess)


def test_mfa_error_message_mentions_browser_fallback():
    sess = _make_session(cookies=[("v-authenticated", "1")])
    with pytest.raises(MFARequiredError, match="browser extraction"):
        login("u@e.com", "p", domain="https://cookidoo.co.uk", locale="en-GB",
              session=sess)


# ---------------------------------------------------------------------------
# Cookie cache tests (use tmp_path + monkeypatch)
# ---------------------------------------------------------------------------

def test_cache_write_and_read(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    # Re-import to pick up the patched env.
    from cookidoo_uploader.cache import read_cached_cookie, write_cached_cookie

    write_cached_cookie("fresh-cookie-value")
    assert read_cached_cookie() == "fresh-cookie-value"


def test_cache_expired_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from cookidoo_uploader.cache import read_cached_cookie, write_cached_cookie

    past = datetime.now(timezone.utc).timestamp() - 1
    write_cached_cookie("old-value", expires_at=past)
    assert read_cached_cookie() is None


def test_cache_skew_treated_as_expired(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from cookidoo_uploader.cache import _SKEW_SECONDS, read_cached_cookie, write_cached_cookie

    # Expires exactly at the skew boundary → should be treated as expired.
    soon = datetime.now(timezone.utc).timestamp() + _SKEW_SECONDS - 1
    write_cached_cookie("almost-expired", expires_at=soon)
    assert read_cached_cookie() is None


def test_cache_file_mode_is_0600(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from cookidoo_uploader.cache import _cache_path, write_cached_cookie

    write_cached_cookie("value")
    path = _cache_path()
    mode = path.stat().st_mode & 0o777
    assert mode == 0o600, f"Expected 0600, got {oct(mode)}"


def test_cache_dir_mode_is_0700(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from cookidoo_uploader.cache import _cache_dir, write_cached_cookie

    write_cached_cookie("value")
    d = _cache_dir()
    mode = d.stat().st_mode & 0o777
    assert mode == 0o700, f"Expected 0700, got {oct(mode)}"


def test_invalidate_cache_removes_file(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from cookidoo_uploader.cache import (
        invalidate_cache,
        read_cached_cookie,
        write_cached_cookie,
    )

    write_cached_cookie("value")
    assert read_cached_cookie() == "value"
    invalidate_cache()
    assert read_cached_cookie() is None


def test_invalidate_cache_is_idempotent(tmp_path, monkeypatch):
    """Calling invalidate_cache() when no file exists must not raise."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from cookidoo_uploader.cache import invalidate_cache

    invalidate_cache()  # no file present — should be a no-op
    invalidate_cache()  # second call also safe


def test_cache_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from cookidoo_uploader.cache import read_cached_cookie

    assert read_cached_cookie() is None


# ---------------------------------------------------------------------------
# get_cookie_via_login() writes to cache
# ---------------------------------------------------------------------------

def test_get_cookie_via_login_caches_cookie(tmp_path, monkeypatch):
    """get_cookie_via_login() should write the cookie to disk after a successful login."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("COOKIDOO_EMAIL", "u@e.com")
    monkeypatch.setenv("COOKIDOO_PASSWORD", "pass")
    monkeypatch.chdir(tmp_path)

    from cookidoo_uploader.cache import read_cached_cookie
    from cookidoo_uploader.login import get_cookie_via_login

    monkeypatch.setattr("cookidoo_uploader.login.login", lambda *a, **kw: "via-login-tok")
    result = get_cookie_via_login()
    assert result == "via-login-tok"
    assert read_cached_cookie() == "via-login-tok"
