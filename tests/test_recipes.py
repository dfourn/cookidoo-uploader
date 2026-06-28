"""Golden / self-validating tests for the built-in recipes."""

import pytest

from cookidoo_uploader import recipes
from cookidoo_uploader.schema import build_payload, validate_payload


@pytest.mark.parametrize("slug", recipes.names())
def test_recipe_payload_self_validates(slug):
    """Every annotation in every built-in recipe must index its own substring."""
    payload = build_payload(recipes.get(slug))
    validate_payload(payload)


@pytest.mark.parametrize("slug", recipes.names())
def test_recipe_payload_is_json_serializable_and_well_formed(slug):
    import json

    payload = build_payload(recipes.get(slug))
    json.dumps(payload)  # must not raise
    assert payload["name"]
    assert payload["ingredients"]
    assert payload["instructions"]
    assert payload["tool"] == ["TM6"]


def test_known_recipe_slugs_present():
    assert set(recipes.names()) >= {"chicken-tikka-masala", "creamy-mushroom-pasta"}
