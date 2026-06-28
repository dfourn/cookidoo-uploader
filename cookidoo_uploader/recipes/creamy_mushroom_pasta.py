"""Creamy Mushroom Pasta — TM6 guided-cooking recipe definition."""

from ..schema import Recipe, step, tts

INGREDIENTS = [
    "300g chestnut mushrooms",
    "280g Quorn chicken-style pieces (optional)",
    "1 onion, halved",
    "2 garlic cloves",
    "35g Parmesan, in chunks",
    "20g butter",
    "1 tbsp olive oil",
    "100ml dry white wine (or 100ml stock)",
    "150ml double cream",
    "A few sprigs fresh thyme (or 1 tsp dried)",
    "200g pasta (tagliatelle, penne, or rigatoni)",
    "Salt & black pepper",
    "Fresh parsley, to serve",
]

INSTRUCTIONS = [
    step("Add 35g Parmesan, in chunks to the mixing bowl (save a little for serving).",
         settings=tts(10, 10),
         ingredient_spans=["35g Parmesan, in chunks"]),
    step("Transfer the grated Parmesan to a bowl and set aside."),
    step("Add 300g chestnut mushrooms to the mixing bowl, halving any large ones.",
         settings=tts(3, 4),
         ingredient_spans=["300g chestnut mushrooms"]),
    step("Transfer the chopped mushrooms to a bowl and set aside."),
    step("Add 1 onion, halved and 2 garlic cloves to the mixing bowl.",
         settings=tts(5, 7),
         ingredient_spans=["1 onion, halved", "2 garlic cloves"]),
    step("Scrape down the bowl. Add 20g butter and 1 tbsp olive oil and saute the base.",
         settings=tts(180, 1, temp=120),
         ingredient_spans=["20g butter", "1 tbsp olive oil"]),
    step("Add to the mixing bowl, then cook with the measuring cup OFF so the "
         "liquid reduces:\n"
         "- the reserved 300g chestnut mushrooms\n"
         "- 100ml dry white wine (or 100ml stock)\n"
         "- A few sprigs fresh thyme (or 1 tsp dried)\n"
         "- 280g Quorn chicken-style pieces (optional), if using",
         settings=tts(600, "soft", temp=100, reverse=True),
         # The mushrooms were already auto-weighed on first use (chop step
         # above), so they are NOT re-weighed here — only the new ingredients
         # in this step get INGREDIENT spans.
         ingredient_spans=["100ml dry white wine (or 100ml stock)",
                           "A few sprigs fresh thyme (or 1 tsp dried)",
                           "280g Quorn chicken-style pieces (optional)"]),
    step("Meanwhile, cook 200g pasta (tagliatelle, penne, or rigatoni) in salted "
         "boiling water until al dente, reserving a mugful of pasta water before draining.",
         ingredient_spans=["200g pasta (tagliatelle, penne, or rigatoni)"]),
    step("Add 150ml double cream and the reserved grated Parmesan. Season with salt "
         "and black pepper, loosening with a splash of pasta water if too thick.",
         settings=tts(120, "soft", temp=90, reverse=True),
         ingredient_spans=["150ml double cream"]),
    step("Divide the drained pasta between serving bowls or containers, then spoon the "
         "sauce over the top. Finish with the reserved Parmesan, fresh parsley, and "
         "black pepper."),
]

RECIPE = Recipe(
    name="Creamy Mushroom Pasta (TM6)",
    ingredients=INGREDIENTS,
    instructions=INSTRUCTIONS,
    total_time=25 * 60,
    prep_time=10 * 60,
    yield_value=2,
)
