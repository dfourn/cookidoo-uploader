"""HTTP client for the Cookidoo created-recipes API."""

import requests

from .config import DOMAIN, HEADERS, LOCALE, UA
from .errors import COOKIE_HINT, CookidooError


class CookidooClient:
    """Thin wrapper around a requests.Session carrying the auth cookie.

    A session can be injected (for tests); otherwise a fresh one is created and
    the `_oauth2_proxy` cookie is set on it.
    """

    def __init__(self, cookie, session=None, domain=DOMAIN, locale=LOCALE):
        self.domain = domain
        self.locale = locale
        self.session = session or requests.Session()
        if cookie is not None:
            self.session.cookies.set("_oauth2_proxy", cookie)

    def _collection_url(self):
        return f"{self.domain}/created-recipes/{self.locale}"

    def _recipe_url(self, recipe_id):
        return f"{self.domain}/created-recipes/{self.locale}/{recipe_id}"

    def _check_ok(self, resp, what):
        """Raise CookidooError on a non-OK response, with the cookie hint on 401/403."""
        if resp.status_code in (401, 403):
            raise CookidooError(f"{what} failed ({resp.status_code}). {COOKIE_HINT}")
        if not resp.ok:
            raise CookidooError(f"{what} failed ({resp.status_code}): {resp.text[:500]}")

    def _parse_json(self, resp, what):
        ctype = resp.headers.get("Content-Type", "")
        if resp.status_code in (401, 403) or "json" not in ctype.lower():
            raise CookidooError(
                f"could not read JSON from {what} (status {resp.status_code}, "
                f"content-type {ctype!r}). {COOKIE_HINT}")
        try:
            return resp.json()
        except ValueError:
            raise CookidooError(f"{what} did not return valid JSON. {COOKIE_HINT}")

    def create_stub(self, name):
        """POST an empty recipe stub and return its id."""
        r = self.session.post(self._collection_url(), headers=HEADERS,
                              json={"recipeName": name}, timeout=20)
        self._check_ok(r, "create POST")
        j = self._parse_json(r, "create POST")
        recipe_id = j.get("recipeId") or j.get("id")
        if not recipe_id:
            raise CookidooError(f"create response had no recipeId/id: {j!r}")
        return recipe_id

    def patch(self, recipe_id, body, what="PATCH"):
        r = self.session.patch(self._recipe_url(recipe_id), headers=HEADERS,
                              json=body, timeout=20)
        self._check_ok(r, what)
        return r

    def verify(self, recipe_id):
        """GET the recipe back and return its recipeContent dict."""
        g = self.session.get(self._recipe_url(recipe_id),
                            headers={"Accept": "application/json", "User-Agent": UA},
                            timeout=20)
        return self._parse_json(g, "verify GET").get("recipeContent", {})

    def upload_recipe(self, payload, update_id=None):
        """Create (or reuse update_id) then PATCH instructions, then metadata.

        Mirrors the two-PATCH flow the web app uses. Returns the recipe id.
        """
        name = payload["name"]
        recipe_id = update_id or self.create_stub(name)
        self.patch(recipe_id, {"instructions": payload["instructions"]},
                   "PATCH instructions")
        meta = {k: payload[k] for k in ("tool", "totalTime", "prepTime", "yield")}
        self.patch(recipe_id,
                   {"name": name, "ingredients": payload["ingredients"], **meta},
                   "PATCH ingredients+metadata")
        return recipe_id
