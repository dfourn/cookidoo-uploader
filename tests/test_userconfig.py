"""Tests for cookidoo_uploader.userconfig and get_cookie_via_login() fall-through.

All tests use monkeypatching — no real credentials, no real config files,
no real keyring, no real network.
"""

import sys
from pathlib import Path

from cookidoo_uploader import userconfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_toml(path: Path, content: str) -> None:
    """Write *content* as a TOML file at *path* (creates parent dirs)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

def test_load_config_empty_when_no_files(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)  # no .cookidoo.toml in cwd either
    cfg = userconfig.load_config()
    assert cfg == {}


def test_load_config_reads_user_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    cfg_path = tmp_path / "cookidoo" / "config.toml"
    _write_toml(cfg_path, '[auth]\nemail = "user@example.com"\n')

    cfg = userconfig.load_config()
    assert cfg["auth"]["email"] == "user@example.com"


def test_load_config_local_overrides_user(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    user_cfg = tmp_path / "cookidoo" / "config.toml"
    _write_toml(user_cfg, '[cookidoo]\ndomain = "https://cookidoo.de"\n')

    local_cfg = tmp_path / ".cookidoo.toml"
    _write_toml(local_cfg, '[cookidoo]\ndomain = "https://cookidoo.co.uk"\n')

    cfg = userconfig.load_config()
    assert cfg["cookidoo"]["domain"] == "https://cookidoo.co.uk"


def test_load_config_explicit_path_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    user_cfg = tmp_path / "cookidoo" / "config.toml"
    _write_toml(user_cfg, '[cookidoo]\ndomain = "https://cookidoo.de"\n')

    explicit = tmp_path / "explicit.toml"
    _write_toml(explicit, '[cookidoo]\ndomain = "https://cookidoo.thermomix.com"\n')

    cfg = userconfig.load_config(config_path=explicit)
    assert cfg["cookidoo"]["domain"] == "https://cookidoo.thermomix.com"


def test_load_config_sections_deep_merged(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    user_cfg = tmp_path / "cookidoo" / "config.toml"
    _write_toml(user_cfg, '[auth]\nemail = "a@b.com"\n[cookidoo]\ndomain = "https://x"\n')

    local_cfg = tmp_path / ".cookidoo.toml"
    _write_toml(local_cfg, '[cookidoo]\nlocale = "de-DE"\n')

    cfg = userconfig.load_config()
    # email from user config and locale from local — neither should clobber the other
    assert cfg["auth"]["email"] == "a@b.com"
    assert cfg["cookidoo"]["domain"] == "https://x"
    assert cfg["cookidoo"]["locale"] == "de-DE"


# ---------------------------------------------------------------------------
# resolve_email
# ---------------------------------------------------------------------------

def test_resolve_email_from_env(monkeypatch):
    monkeypatch.setenv("COOKIDOO_EMAIL", "env@example.com")
    assert userconfig.resolve_email(config={}) == "env@example.com"


def test_resolve_email_env_takes_priority_over_config(monkeypatch):
    monkeypatch.setenv("COOKIDOO_EMAIL", "env@example.com")
    cfg = {"auth": {"email": "cfg@example.com"}}
    assert userconfig.resolve_email(config=cfg) == "env@example.com"


def test_resolve_email_from_config(monkeypatch):
    monkeypatch.delenv("COOKIDOO_EMAIL", raising=False)
    cfg = {"auth": {"email": "cfg@example.com"}}
    assert userconfig.resolve_email(config=cfg) == "cfg@example.com"


def test_resolve_email_returns_none_when_unconfigured(monkeypatch):
    monkeypatch.delenv("COOKIDOO_EMAIL", raising=False)
    assert userconfig.resolve_email(config={}) is None


# ---------------------------------------------------------------------------
# resolve_password — precedence
# ---------------------------------------------------------------------------

def _mock_keyring(monkeypatch, password):
    """Inject a mock keyring module returning *password* (or None if falsy)."""

    class _MockKeyring:
        @staticmethod
        def get_password(service, username):
            return password

        @staticmethod
        def set_password(service, username, pw):
            pass

    monkeypatch.setitem(sys.modules, "keyring", _MockKeyring())


def test_resolve_password_from_env(monkeypatch):
    monkeypatch.setenv("COOKIDOO_PASSWORD", "env-pass")
    # Keyring should never be reached.
    assert userconfig.resolve_password("u@e.com", config={}) == "env-pass"


def test_resolve_password_env_beats_keyring(monkeypatch):
    monkeypatch.setenv("COOKIDOO_PASSWORD", "env-pass")
    _mock_keyring(monkeypatch, "keyring-pass")
    assert userconfig.resolve_password("u@e.com", config={}) == "env-pass"


def test_resolve_password_from_keyring(monkeypatch):
    monkeypatch.delenv("COOKIDOO_PASSWORD", raising=False)
    _mock_keyring(monkeypatch, "keyring-pass")
    assert userconfig.resolve_password("u@e.com", config={}) == "keyring-pass"


def test_resolve_password_keyring_beats_config(monkeypatch):
    monkeypatch.delenv("COOKIDOO_PASSWORD", raising=False)
    _mock_keyring(monkeypatch, "keyring-pass")
    cfg = {"auth": {"password": "config-pass"}}
    assert userconfig.resolve_password("u@e.com", config=cfg) == "keyring-pass"


def test_resolve_password_from_config_when_no_keyring(monkeypatch):
    monkeypatch.delenv("COOKIDOO_PASSWORD", raising=False)
    # Simulate keyring not installed.
    monkeypatch.setitem(sys.modules, "keyring", None)
    cfg = {"auth": {"password": "config-pass"}}
    # Keyring import will fail (None is not a module), _keyring_get returns None.
    assert userconfig.resolve_password("u@e.com", config=cfg) == "config-pass"


def test_resolve_password_returns_none_no_tty_no_config(monkeypatch):
    monkeypatch.delenv("COOKIDOO_PASSWORD", raising=False)
    _mock_keyring(monkeypatch, None)
    # stdin.isatty() returns False in the test runner.
    assert userconfig.resolve_password("u@e.com", config={}) is None


# ---------------------------------------------------------------------------
# get_cookie_via_login — fall-through when no credentials
# ---------------------------------------------------------------------------

def test_get_cookie_via_login_returns_none_when_no_email(tmp_path, monkeypatch):
    monkeypatch.delenv("COOKIDOO_EMAIL", raising=False)
    monkeypatch.delenv("COOKIDOO_PASSWORD", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)  # no .cookidoo.toml

    from cookidoo_uploader.login import get_cookie_via_login
    assert get_cookie_via_login() is None


def test_get_cookie_via_login_returns_none_when_no_password(tmp_path, monkeypatch):
    monkeypatch.setenv("COOKIDOO_EMAIL", "u@e.com")
    monkeypatch.delenv("COOKIDOO_PASSWORD", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    _mock_keyring(monkeypatch, None)

    from cookidoo_uploader.login import get_cookie_via_login
    # No config, no keyring, no TTY → returns None.
    assert get_cookie_via_login() is None


def test_get_cookie_via_login_calls_login_and_caches(tmp_path, monkeypatch):
    """Integration: when credentials are present, login() is called and result cached."""
    monkeypatch.setenv("COOKIDOO_EMAIL", "u@e.com")
    monkeypatch.setenv("COOKIDOO_PASSWORD", "pass")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    # Patch login() to avoid real HTTP.
    monkeypatch.setattr("cookidoo_uploader.login.login", lambda *a, **kw: "mocked-cookie")

    from cookidoo_uploader.cache import read_cached_cookie
    from cookidoo_uploader.login import get_cookie_via_login

    result = get_cookie_via_login()
    assert result == "mocked-cookie"
    assert read_cached_cookie() == "mocked-cookie"


# ---------------------------------------------------------------------------
# _keyring_set helper (via userconfig)
# ---------------------------------------------------------------------------

def test_keyring_set_returns_true_on_success(monkeypatch):
    stored = {}

    class _MockKeyring:
        @staticmethod
        def get_password(service, username):
            return stored.get(username)

        @staticmethod
        def set_password(service, username, pw):
            stored[username] = pw

    monkeypatch.setitem(sys.modules, "keyring", _MockKeyring())
    ok = userconfig._keyring_set("u@e.com", "mysecret")
    assert ok is True
    assert stored["u@e.com"] == "mysecret"


def test_keyring_set_returns_false_when_unavailable(monkeypatch):
    monkeypatch.setitem(sys.modules, "keyring", None)
    ok = userconfig._keyring_set("u@e.com", "mysecret")
    assert ok is False
