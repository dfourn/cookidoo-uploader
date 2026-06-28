"""Registry of built-in recipes, keyed by CLI slug."""

from . import chicken_tikka_masala, creamy_mushroom_pasta

RECIPES = {
    "chicken-tikka-masala": chicken_tikka_masala.RECIPE,
    "creamy-mushroom-pasta": creamy_mushroom_pasta.RECIPE,
}


def get(slug):
    return RECIPES.get(slug)


def names():
    return sorted(RECIPES)
