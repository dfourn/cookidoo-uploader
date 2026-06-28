"""Persist the _oauth2_proxy cookie between runs.

The cache file is written with mode 0600 (owner read/write only) to the
cookidoo config directory.  The directory itself is created at 0700.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

_SKEW_SECONDS = 300  # treat cookie as expired 5 min before its real expiry
_DEFAULT_TTL = 3600  # conservative TTL when the cookie jar carries no expiry


def _cache_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "cookidoo"


def _cache_path() -> Path:
    return _cache_dir() / "cookie.json"


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)
    os.chmod(p, 0o700)


def write_cached_cookie(value: str, expires_at: float | None = None) -> None:
    """Write *value* to the cache file with 0600 permissions.

    *expires_at* is a UTC Unix timestamp; when omitted a conservative default
    TTL is applied.
    """
    if expires_at is None:
        expires_at = datetime.now(timezone.utc).timestamp() + _DEFAULT_TTL
    d = _cache_dir()
    _ensure_dir(d)
    path = _cache_path()
    data = json.dumps({"value": value, "expires_at": expires_at})
    # Write via a temp file then rename for atomicity.
    tmp = path.with_suffix(".tmp")
    tmp.write_text(data, encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.rename(path)


def read_cached_cookie() -> str | None:
    """Return the cached cookie if it exists and is not (nearly) expired.

    Returns ``None`` on any error or when the cache is missing / stale.
    """
    path = _cache_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        value: str = data["value"]
        expires_at: float = float(data["expires_at"])
        now = datetime.now(timezone.utc).timestamp()
        if now < expires_at - _SKEW_SECONDS:
            return value
        return None
    except Exception:
        return None


def invalidate_cache() -> None:
    """Delete the cached cookie (call on 401/403 to force re-login)."""
    path = _cache_path()
    try:
        path.unlink()
    except FileNotFoundError:
        pass
