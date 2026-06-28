"""User configuration: TOML config loading and credential resolution.

Config file locations (later entries win):
  1. ``$XDG_CONFIG_HOME/cookidoo/config.toml``  (default: ``~/.config/cookidoo/config.toml``)
  2. ``./.cookidoo.toml``  (project-local; should be gitignored)
  3. An explicit path passed to :func:`load_config`

Credential precedence (highest → lowest):
  1. Environment variables (``COOKIDOO_EMAIL`` / ``COOKIDOO_PASSWORD``)
  2. OS keychain via ``keyring`` (lazy import; optional dep)
  3. Config-file plaintext ``[auth] password`` (discouraged — prefer keyring)
  4. Interactive ``getpass`` prompt (only when stdin is a TTY and email is known)
"""

import os
import sys
import tomllib
import warnings
from pathlib import Path
from typing import Optional

_KEYRING_SERVICE = "cookidoo-uploader"


# ---------------------------------------------------------------------------
# Config directory / file helpers
# ---------------------------------------------------------------------------

def _config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "cookidoo"


def _load_toml(path: Path) -> dict:
    """Return the parsed TOML file at *path*, or ``{}`` if missing/unreadable."""
    if not path.exists():
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def _deep_merge(base: dict, override: dict) -> None:
    """Merge *override* into *base* in-place; nested dicts are merged recursively."""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def _warn_plaintext_password(path: Path) -> None:
    """Warn when a config file that contains a password is not 0600."""
    try:
        mode = path.stat().st_mode & 0o777
        if mode != 0o600:
            warnings.warn(
                f"Config file {path} has permissions {oct(mode)} but contains "
                "credentials — it should be 0600.  Run: chmod 600 " + str(path),
                stacklevel=4,
            )
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_config(config_path: Optional[Path] = None) -> dict:
    """Return merged configuration from all config file sources.

    Merges in the order: user config → local ``.cookidoo.toml`` → explicit
    *config_path* (if supplied).  Dict sections are merged recursively; scalar
    values from later sources win.
    """
    merged: dict = {}

    user_cfg = _config_dir() / "config.toml"
    _deep_merge(merged, _load_toml(user_cfg))

    local_cfg = Path(".cookidoo.toml")
    _deep_merge(merged, _load_toml(local_cfg))

    if config_path is not None:
        _deep_merge(merged, _load_toml(Path(config_path)))

    return merged


def resolve_email(config: Optional[dict] = None) -> Optional[str]:
    """Return the configured email address, or ``None`` if not found.

    Precedence: ``COOKIDOO_EMAIL`` env var → ``[auth] email`` in config.
    """
    env_val = os.environ.get("COOKIDOO_EMAIL")
    if env_val:
        return env_val
    if config is None:
        config = load_config()
    return config.get("auth", {}).get("email") or None


def _keyring_get(email: str) -> Optional[str]:
    """Return the keychain password for *email*, or ``None`` on any error."""
    try:
        import keyring  # type: ignore[import]
        return keyring.get_password(_KEYRING_SERVICE, email)
    except Exception:
        return None


def _keyring_set(email: str, password: str) -> bool:
    """Store *password* in the keychain for *email*. Returns ``True`` on success."""
    try:
        import keyring  # type: ignore[import]
        keyring.set_password(_KEYRING_SERVICE, email, password)
        return True
    except Exception:
        return False


def resolve_password(email: str, config: Optional[dict] = None) -> Optional[str]:
    """Return the password for *email*, or ``None`` if none can be found.

    Precedence: ``COOKIDOO_PASSWORD`` env var → keyring → config-file plaintext
    → interactive ``getpass`` prompt (only when stdin is a TTY).

    Never logs or echoes the password.
    """
    # 1. Environment variable.
    env_val = os.environ.get("COOKIDOO_PASSWORD")
    if env_val:
        return env_val

    # 2. OS keychain (lazy import — optional dep).
    kr_val = _keyring_get(email)
    if kr_val:
        return kr_val

    # 3. Config-file plaintext (discouraged).
    if config is None:
        config = load_config()
    plaintext = config.get("auth", {}).get("password")
    if plaintext:
        # Check file permissions and warn if insecure.
        cfg_path = _config_dir() / "config.toml"
        if cfg_path.exists():
            _warn_plaintext_password(cfg_path)
        return plaintext

    # 4. Interactive prompt (only when a TTY is present).
    if sys.stdin.isatty():
        import getpass
        try:
            pw = getpass.getpass(f"Cookidoo password for {email}: ")
            return pw if pw else None
        except (KeyboardInterrupt, EOFError):
            return None

    return None
