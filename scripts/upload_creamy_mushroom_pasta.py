#!/usr/bin/env python3
"""
Upload "Creamy Mushroom Pasta" to Cookidoo as a Created Recipe WITH
programmable guided-cooking steps (TTS annotations: time / temperature /
speed / reverse), using the schema confirmed from a captured browser PATCH.

Confirmed TTS schema (from cookidoo_investigation/*.har):
  annotation = {
    "type": "TTS",
    "data": {
        "speed": "10" | "soft",          # string; "soft" == Speed Soft Stir
        "time": <int seconds>,
        "direction": "CCW",              # present only for REVERSE rotation
        "temperature": {"value": "100", "unit": "C"}   # omit when no heat
    },
    "position": {"offset": <int>, "length": <int>}     # span in the step text
  }
Ingredient auto-weighing uses {"type":"INGREDIENT","data":{"description": <exact ingredient text>}, ...}.

Auth: reads the _oauth2_proxy cookie from $COOKIDOO_COOKIE, or falls back to
reading it straight from the browser via get_cookidoo_cookie.py.

Usage:
    cookiput_venv/bin/python scripts/upload_creamy_mushroom_pasta.py --dry-run
    cookiput_venv/bin/python scripts/upload_creamy_mushroom_pasta.py            # live upload
"""

import argparse
import json
import os
import sys
import requests

DOMAIN = "https://cookidoo.co.uk"
LOCALE = "en-GB"

# ---------------------------------------------------------------------------
# Recipe definition
# ---------------------------------------------------------------------------

NAME = "Creamy Mushroom Pasta (TM6)"

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
    # Simpler, robust label: just join everything with "/"
    label = "/".join(parts)
    return data, label


def step(main_text, settings=None, ingredient_spans=None):
    """Assemble a STEP with optional TTS settings + INGREDIENT auto-weigh spans.

    ingredient_spans: list of exact substrings present in main_text that should
    auto-link to ingredients (their description must match an INGREDIENTS entry).
    """
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
             # NOTE: the mushrooms were already auto-weighed on first use (chop
             # step above), so they are NOT re-weighed here -- only the new
             # ingredients in this step get INGREDIENT spans.
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


# NOTE on the write (PATCH) schema, confirmed empirically against the API:
#   - ingredients : list of {"type": "INGREDIENT", "text": <str>}  (NOT plain strings)
#   - totalTime / prepTime : integer SECONDS (NOT the ISO "PT25M" the GET returns)
#   - yield : key is "yield" (NOT "recipeYield", which the PATCH silently ignores)
TOOL = ["TM6"]

METADATA = {
    "tool": TOOL,
    "totalTime": 25 * 60,
    "prepTime": 10 * 60,
    "yield": {"value": 2, "unitText": "portion"},
}

# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

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
    # fall back to reading from the browser
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
    r = session.patch(url, headers=HEADERS, json=body, timeout=20)
    return r


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
        # update existing recipe in place (no duplicate)
        recipe_id = args.update_id
        print(f"Updating existing recipe: {recipe_id}")
    else:
        # 1. create stub
        r = session.post(f"{DOMAIN}/created-recipes/{LOCALE}",
                         headers=HEADERS, json={"recipeName": NAME}, timeout=20)
        r.raise_for_status()
        j = parse_json(r, "create POST")
        recipe_id = j.get("recipeId") or j.get("id")
        if not recipe_id:
            print(f"ERROR: create response had no recipeId/id: {j!r}", file=sys.stderr)
            sys.exit(1)
        print(f"Created recipe stub: {recipe_id}")

    # 2. instructions (confirmed schema)
    r = patch(session, recipe_id, {"instructions": instructions})
    print(f"PATCH instructions -> {r.status_code}")
    if not r.ok:
        print(r.text[:500], file=sys.stderr)
        r.raise_for_status()

    # 3. ingredients + metadata (schema confirmed; see METADATA note above)
    r = patch(session, recipe_id, {"name": NAME, "ingredients": ingredient_objs, **metadata})
    print(f"PATCH ingredients+metadata -> {r.status_code}")
    if not r.ok:
        print(r.text[:500], file=sys.stderr)
        r.raise_for_status()

    # 4. verify by reading it back
    g = session.get(f"{DOMAIN}/created-recipes/{LOCALE}/{recipe_id}",
                    headers={"Accept": "application/json", "User-Agent": HEADERS["User-Agent"]},
                    timeout=20)
    rc = parse_json(g, "verify GET").get("recipeContent", {})
    print("\n--- VERIFY (recipeContent) ---")
    print("name:", rc.get("name"))
    print("ingredients:", len(rc.get("recipeIngredient", [])), "->", rc.get("recipeIngredient", [])[:2])
    print("instructions:", len(rc.get("recipeInstructions", [])))
    for ins in rc.get("recipeInstructions", []):
        print("  -", ins)
    print("tool:", rc.get("tool"), "| totalTime:", rc.get("totalTime"),
          "| prepTime:", rc.get("prepTime"), "| yield:", rc.get("recipeYield"))
    print(f"\nView at: {DOMAIN}/created-recipes/{LOCALE}/{recipe_id}")


if __name__ == "__main__":
    main()
