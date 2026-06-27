#!/usr/bin/env python3
"""
Upload "Chicken Tikka Masala" to Cookidoo as a Created Recipe WITH
programmable guided-cooking steps (TTS annotations: time / temperature /
speed / reverse), using the schema confirmed from a captured browser PATCH.

Schema notes (see cookidoo_investigation/*.har and the upload schema memory):
  - ingredients : list of {"type":"INGREDIENT","text":<str>}  (NOT plain strings)
  - instructions: [{type:"STEP", text, annotations:[TTS/INGREDIENT...]}]
  - TTS annotation: {"type":"TTS","data":{speed,time,[direction],[temperature]},
                     "position":{offset,length}}  span covers settings label in text
        speed     : "1".."10" or "soft" (== Speed Soft Stir)
        time      : int seconds
        direction : "CCW" only for REVERSE
        temperature: {"value":"100","unit":"C"} (omit when unheated)
  - INGREDIENT auto-weigh: {"type":"INGREDIENT","data":{"description":<exact text>}, position}
  - totalTime/prepTime : int SECONDS (NOT ISO "PT25M")
  - yield : key is "yield" {value, unitText:"portion"} (recipeYield is ignored)
  - tool : ["TM6"]

Auth: reads _oauth2_proxy from $COOKIDOO_COOKIE, else from the browser via
get_cookidoo_cookie.py.

Usage:
    cookiput_venv/bin/python scripts/upload_chicken_tikka_masala.py --dry-run
    cookiput_venv/bin/python scripts/upload_chicken_tikka_masala.py          # live
"""

import argparse
import json
import os
import sys
import requests

DOMAIN = "https://cookidoo.co.uk"
LOCALE = "en-GB"

NAME = "Chicken Tikka Masala (TM6)"

# Single-value quantities for auto-weigh (markdown keeps the 650-950g range).
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


def fmt_time(secs):
    return f"{secs} sec" if secs < 60 else f"{secs // 60} min"


def tts(time, speed, temp=None, reverse=False):
    """Build a TTS data dict + its human-readable settings label."""
    data = {"speed": str(speed), "time": time}
    if reverse:
        data["direction"] = "CCW"
    if temp is not None:
        data["temperature"] = {"value": str(temp), "unit": "C"}

    parts = [fmt_time(time)]
    if temp is not None:
        parts.append(f"{temp}°C")
    parts.append("speed soft stir" if str(speed) == "soft" else f"speed {speed}")
    if reverse:
        parts.append("reverse")
    label = "/".join(parts)
    return data, label


def step(main_text, settings=None, ingredient_spans=None):
    """Assemble a STEP with optional TTS settings + INGREDIENT auto-weigh spans."""
    text = main_text
    annotations = []

    cursor = 0
    for span in ingredient_spans or []:
        off = text.find(span, cursor)
        if off < 0:
            raise ValueError(
                f"ingredient span {span!r} not found at/after offset {cursor} "
                f"in step text: {text!r}")
        annotations.append({
            "type": "INGREDIENT",
            "data": {"description": span},
            "position": {"offset": off, "length": len(span)},
        })
        cursor = off + len(span)

    if settings is not None:
        data, label = settings
        text = f"{text} {label}"
        off = len(text) - len(label)
        annotations.append({
            "type": "TTS",
            "data": data,
            "position": {"offset": off, "length": len(label)},
        })

    s = {"type": "STEP", "text": text}
    if annotations:
        s["annotations"] = annotations
    return s


def build_instructions():
    return [
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


TOOL = ["TM6"]

METADATA = {
    "tool": TOOL,
    "totalTime": 50 * 60,
    "prepTime": 15 * 60,
    "yield": {"value": 3, "unitText": "portion"},
}

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


def get_cookie():
    val = os.getenv("COOKIDOO_COOKIE")
    if val:
        return val
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import get_cookidoo_cookie
    res = get_cookidoo_cookie.find_cookie()
    if not res:
        print("No Cookidoo cookie found (set $COOKIDOO_COOKIE or log in to Cookidoo).",
              file=sys.stderr)
        sys.exit(1)
    return res[0]


def patch(session, recipe_id, body):
    url = f"{DOMAIN}/created-recipes/{LOCALE}/{recipe_id}"
    return session.patch(url, headers=HEADERS, json=body, timeout=20)


COOKIE_HINT = (
    "Cookie appears expired (server returned a login redirect / non-JSON, "
    "or 401/403). Log out and back in to Cookidoo and refresh COOKIDOO_COOKIE, "
    "or re-run get_cookidoo_cookie.py."
)


def parse_json(resp, what):
    """Return resp.json(), with an actionable error on auth/HTML responses."""
    ctype = resp.headers.get("Content-Type", "")
    if resp.status_code in (401, 403) or "json" not in ctype.lower():
        print(f"ERROR: could not read JSON from {what} "
              f"(status {resp.status_code}, content-type {ctype!r}).",
              file=sys.stderr)
        print(COOKIE_HINT, file=sys.stderr)
        sys.exit(1)
    try:
        return resp.json()
    except ValueError:
        print(f"ERROR: {what} did not return valid JSON.", file=sys.stderr)
        print(COOKIE_HINT, file=sys.stderr)
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print payload, don't upload")
    ap.add_argument("--update-id", metavar="RECIPE_ID",
                    help="PATCH this existing recipe in place instead of creating a new one")
    ap.add_argument("--tool", choices=["TM6", "TM7"], default="TM6",
                    help="Thermomix model to target (default TM6; TM7 is unverified)")
    args = ap.parse_args()

    if args.tool == "TM7":
        print("WARNING: --tool TM7 is untested/unverified against this private "
              "API (schema was reverse-engineered from TM6 traffic).", file=sys.stderr)
    metadata = {**METADATA, "tool": [args.tool]}

    instructions = build_instructions()
    ingredient_objs = [{"type": "INGREDIENT", "text": t} for t in INGREDIENTS]
    payload_preview = {
        "name": NAME,
        "ingredients": ingredient_objs,
        "instructions": instructions,
        **metadata,
    }

    if args.dry_run:
        print(json.dumps(payload_preview, indent=2, ensure_ascii=False))
        print(f"\n[dry-run] {len(instructions)} steps, "
              f"{sum('annotations' in s for s in instructions)} with annotations.",
              file=sys.stderr)
        return

    cookie = get_cookie()
    session = requests.Session()
    session.cookies.set("_oauth2_proxy", cookie)

    if args.update_id:
        recipe_id = args.update_id
        print(f"Updating existing recipe: {recipe_id}")
    else:
        r = session.post(f"{DOMAIN}/created-recipes/{LOCALE}",
                         headers=HEADERS, json={"recipeName": NAME}, timeout=20)
        r.raise_for_status()
        j = parse_json(r, "create POST")
        recipe_id = j.get("recipeId") or j.get("id")
        if not recipe_id:
            print(f"ERROR: create response had no recipeId/id: {j!r}", file=sys.stderr)
            sys.exit(1)
        print(f"Created recipe stub: {recipe_id}")

    r = patch(session, recipe_id, {"instructions": instructions})
    print(f"PATCH instructions -> {r.status_code}")
    if not r.ok:
        print(r.text[:500], file=sys.stderr)
        r.raise_for_status()

    r = patch(session, recipe_id, {"name": NAME, "ingredients": ingredient_objs, **metadata})
    print(f"PATCH ingredients+metadata -> {r.status_code}")
    if not r.ok:
        print(r.text[:500], file=sys.stderr)
        r.raise_for_status()

    g = session.get(f"{DOMAIN}/created-recipes/{LOCALE}/{recipe_id}",
                    headers={"Accept": "application/json", "User-Agent": HEADERS["User-Agent"]},
                    timeout=20)
    rc = parse_json(g, "verify GET").get("recipeContent", {})
    print("\n--- VERIFY (recipeContent) ---")
    print("name:", rc.get("name"))
    print("ingredients:", len(rc.get("recipeIngredient", [])))
    print("instructions:", len(rc.get("recipeInstructions", [])))
    print("tool:", rc.get("tool"), "| totalTime:", rc.get("totalTime"),
          "| prepTime:", rc.get("prepTime"), "| yield:", rc.get("recipeYield"))
    print(f"\nView at: {DOMAIN}/created-recipes/{LOCALE}/{recipe_id}")


if __name__ == "__main__":
    main()
