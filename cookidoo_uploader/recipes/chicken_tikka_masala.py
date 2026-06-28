"""Chicken Tikka Masala — TM6 guided-cooking recipe definition."""

from ..schema import Recipe, step, tts

INGREDIENTS = [
    # Marinade
    "950g chicken breast fillets, cut into bite-size chunks",
    "4 tbsp natural yogurt (for the marinade)",
    "1.5 tsp garam masala (for the marinade)",
    "1.5 tsp tikka curry powder (for the marinade)",
    "Salt & pepper",
    # Sauce
    "3 onions, halved",
    "4 garlic cloves",
    "1 large piece fresh ginger, peeled",
    "1.5 tbsp olive oil",
    "1 tbsp tikka curry powder (for the sauce)",
    "1.5 tsp garam masala (for the sauce)",
    "1.5 tsp ground cumin",
    "1.5 tsp ground coriander",
    "3/4 tsp turmeric",
    "1.5 tbsp tomato puree",
    "1 tin chopped tomatoes (400g)",
    "1 tin coconut milk (400ml)",
    "1 tbsp natural yogurt (to finish)",
    # To serve
    "Basmati rice",
    "Fresh coriander, chopped",
    "Lemon, to squeeze",
]

INSTRUCTIONS = [
    step("Marinate the chicken: in a bowl, mix together the following, then "
         "season with salt and pepper and set aside while you make the sauce "
         "(30 min if you have time):\n"
         "- 950g chicken breast fillets, cut into bite-size chunks\n"
         "- 4 tbsp natural yogurt (for the marinade)\n"
         "- 1.5 tsp garam masala (for the marinade)\n"
         "- 1.5 tsp tikka curry powder (for the marinade)",
         ingredient_spans=[
             "950g chicken breast fillets, cut into bite-size chunks",
             "4 tbsp natural yogurt (for the marinade)",
             "1.5 tsp garam masala (for the marinade)",
             "1.5 tsp tikka curry powder (for the marinade)",
         ]),
    step("Add to the mixing bowl, then chop and scrape down the bowl:\n"
         "- 3 onions, halved\n"
         "- 4 garlic cloves\n"
         "- 1 large piece fresh ginger, peeled",
         settings=tts(5, 7),
         ingredient_spans=["3 onions, halved", "4 garlic cloves",
                           "1 large piece fresh ginger, peeled"]),
    step("Add 1.5 tbsp olive oil and saute the base.",
         settings=tts(300, 1, temp=120),
         ingredient_spans=["1.5 tbsp olive oil"]),
    step("Add the following, then cook to toast the spices:\n"
         "- 1 tbsp tikka curry powder (for the sauce)\n"
         "- 1.5 tsp garam masala (for the sauce)\n"
         "- 1.5 tsp ground cumin\n"
         "- 1.5 tsp ground coriander\n"
         "- 3/4 tsp turmeric\n"
         "- 1.5 tbsp tomato puree",
         settings=tts(120, 1, temp=120),
         ingredient_spans=["1 tbsp tikka curry powder (for the sauce)",
                           "1.5 tsp garam masala (for the sauce)",
                           "1.5 tsp ground cumin", "1.5 tsp ground coriander",
                           "3/4 tsp turmeric", "1.5 tbsp tomato puree"]),
    step("Add the following, then simmer with the measuring cup on:\n"
         "- 1 tin chopped tomatoes (400g)\n"
         "- 1 tin coconut milk (400ml)",
         settings=tts(900, 1, temp=100, reverse=True),
         ingredient_spans=["1 tin chopped tomatoes (400g)",
                           "1 tin coconut milk (400ml)"]),
    step("Optional, for a smoother sauce: blend briefly. Skip for a chunkier sauce.",
         settings=tts(10, 6)),
    step("Add the marinated chicken to the sauce and cook until cooked through.",
         settings=tts(1320, "soft", temp=100, reverse=True)),
    step("Take the sauce off the boil, then stir in 1 tbsp natural yogurt (to finish) "
         "so it doesn't split. Taste and adjust salt.",
         ingredient_spans=["1 tbsp natural yogurt (to finish)"]),
    step("Meanwhile, cook the Basmati rice (e.g. Yum Asia rice cooker on the "
         "LONG GRAIN program, ~1 cup per person) so it is ready when the chicken "
         "is done.",
         ingredient_spans=["Basmati rice"]),
    step("Serve the curry over the rice, scattered with Fresh coriander, chopped "
         "and a squeeze of Lemon, to squeeze.",
         ingredient_spans=["Fresh coriander, chopped", "Lemon, to squeeze"]),
]

RECIPE = Recipe(
    name="Chicken Tikka Masala (TM6)",
    ingredients=INGREDIENTS,
    instructions=INSTRUCTIONS,
    total_time=50 * 60,
    prep_time=15 * 60,
    yield_value=3,
)
