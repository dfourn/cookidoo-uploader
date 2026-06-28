"""Client tests using a fake session — no real HTTP."""

import pytest

from cookidoo_uploader.client import CookidooClient
from cookidoo_uploader.errors import CookidooError


class FakeResponse:
    def __init__(self, status=200, json_data=None, content_type="application/json",
                 text=""):
        self.status_code = status
        self._json = json_data
        self.headers = {"Content-Type": content_type}
        self.text = text

    @property
    def ok(self):
        return self.status_code < 400

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


class FakeSession:
    """Records requests and returns queued responses in order."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
        self.cookies = type("Jar", (), {"set": lambda *a, **k: None})()

    def _next(self, method, url, **kw):
        self.calls.append((method, url, kw.get("json")))
        return self._responses.pop(0)

    def post(self, url, **kw):
        return self._next("POST", url, **kw)

    def patch(self, url, **kw):
        return self._next("PATCH", url, **kw)

    def get(self, url, **kw):
        return self._next("GET", url, **kw)


def make_client(responses):
    return CookidooClient("cookie", session=FakeSession(responses))


def test_create_stub_returns_id():
    c = make_client([FakeResponse(json_data={"recipeId": "abc123"})])
    assert c.create_stub("My Recipe") == "abc123"


def test_create_stub_accepts_id_fallback_key():
    c = make_client([FakeResponse(json_data={"id": "xyz"})])
    assert c.create_stub("X") == "xyz"


def test_auth_failure_raises_with_hint():
    c = make_client([FakeResponse(status=401, content_type="text/html",
                                  text="<html>login</html>")])
    with pytest.raises(CookidooError) as e:
        c.create_stub("X")
    assert "refresh COOKIDOO_COOKIE" in str(e.value)


def test_non_json_response_raises():
    c = make_client([FakeResponse(status=200, content_type="text/html",
                                  text="<html>")])
    with pytest.raises(CookidooError):
        c.create_stub("X")


def test_patch_failure_raises_instead_of_silent_success():
    c = make_client([FakeResponse(status=400, text="bad annotation")])
    with pytest.raises(CookidooError, match="PATCH instructions failed"):
        c.patch("rid", {"instructions": []}, "PATCH instructions")


def test_upload_recipe_does_create_then_two_patches():
    sess = FakeSession([
        FakeResponse(json_data={"recipeId": "r1"}),   # create
        FakeResponse(json_data={}),                   # PATCH instructions
        FakeResponse(json_data={}),                   # PATCH metadata
    ])
    c = CookidooClient("cookie", session=sess)
    payload = {
        "name": "N",
        "ingredients": [{"type": "INGREDIENT", "text": "x"}],
        "instructions": [{"type": "STEP", "text": "do"}],
        "tool": ["TM6"], "totalTime": 1, "prepTime": 1,
        "yield": {"value": 1, "unitText": "portion"},
    }
    rid = c.upload_recipe(payload)
    assert rid == "r1"
    methods = [m for m, _, _ in sess.calls]
    assert methods == ["POST", "PATCH", "PATCH"]
    # first PATCH carries instructions, second carries name+ingredients+metadata
    assert "instructions" in sess.calls[1][2]
    assert sess.calls[2][2]["name"] == "N"
    assert sess.calls[2][2]["tool"] == ["TM6"]


def test_upload_recipe_with_update_id_skips_create():
    sess = FakeSession([FakeResponse(json_data={}), FakeResponse(json_data={})])
    c = CookidooClient("cookie", session=sess)
    payload = {
        "name": "N", "ingredients": [], "instructions": [],
        "tool": ["TM6"], "totalTime": 1, "prepTime": 1,
        "yield": {"value": 1, "unitText": "portion"},
    }
    rid = c.upload_recipe(payload, update_id="existing")
    assert rid == "existing"
    assert [m for m, _, _ in sess.calls] == ["PATCH", "PATCH"]
