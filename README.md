# Cookidoo Uploader

Upload your own recipes to [Cookidoo](https://cookidoo.co.uk) as **Created Recipes**
with fully programmable **TM6 guided-cooking steps** — each step can carry the
time / temperature / speed / reverse settings that drive the machine, plus
auto-weigh ingredient annotations.

This talks directly to the same private `created-recipes` API the Cookidoo web
app uses, with the request schema reverse-engineered from captured browser
traffic.

## How it works

1. **Auth** — uses your existing browser login. There's no public API, so
   requests are authenticated with the `_oauth2_proxy` session cookie.
2. **Create** — `POST /created-recipes/{locale}` creates an empty recipe stub
   and returns its id.
3. **Fill in** — `PATCH /created-recipes/{locale}/{id}` sets the name,
   ingredients, instructions (with TM6 annotations) and metadata.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Authentication

The scripts read the `_oauth2_proxy` cookie in one of two ways:

- **Automatic** — `scripts/get_cookidoo_cookie.py` reads it straight from your
  installed browser (Chrome/Safari/Firefox/Edge/Brave). On macOS the first run
  triggers a one-time Keychain prompt to decrypt the browser cookie store.
- **Manual** — set it yourself if you'd rather not touch the browser store:

  ```bash
  export COOKIDOO_COOKIE='<value of the _oauth2_proxy cookie>'
  ```

  Get the value from DevTools → Application → Cookies → `_oauth2_proxy` while
  logged in to Cookidoo. It expires periodically; log out/in to refresh.

> The cookie is a live session credential. Never commit it — `.har` files and
> `.env` are gitignored for this reason.

## Usage

Each `upload_*.py` script encodes one recipe. Preview the JSON payload without
sending anything:

```bash
python scripts/upload_chicken_tikka_masala.py --dry-run
```

Create it live in your Cookidoo account:

```bash
python scripts/upload_chicken_tikka_masala.py
```

Re-run against an existing recipe instead of creating a new one:

```bash
python scripts/upload_chicken_tikka_masala.py --update-id <RECIPE_ID>
```

To attach a photo, see `scripts/upload_recipe_image.py`.

The source recipes these scripts are built from live in [`example/`](example/)
as plain Markdown — a good template for writing your own.

## Writing a new recipe

Copy one of the `upload_*.py` scripts and edit three things:

- `INGREDIENTS` — list of strings. Each becomes
  `{"type": "INGREDIENT", "text": ...}`.
- `build_instructions()` — one `step(...)` per guided step. Use the helpers:
  - `tts(time, speed, temp=None, reverse=False)` — attaches TM6 settings. A
    human-readable label (`5 min/100°C/speed 1/reverse`) is appended to the
    step text and the matching span is annotated for guided cooking.
  - `step(text, settings=tts(...), ingredient_spans=[...])` — `ingredient_spans`
    are exact substrings of the step text that get tagged for auto-weighing.
- `METADATA` — `tool`, `totalTime`, `prepTime` (seconds), `yield`.

## API schema notes

Confirmed from captured `PATCH` traffic — the non-obvious bits:

| Field | Shape |
| --- | --- |
| `ingredients` | `[{"type": "INGREDIENT", "text": "<str>"}]` — objects, **not** plain strings |
| `instructions` | `[{"type": "STEP", "text": "<str>", "annotations": [...]}]` |
| TTS annotation | `{"type": "TTS", "data": {speed, time, [direction], [temperature]}, "position": {offset, length}}` |
| &nbsp;&nbsp;`speed` | `"1".."10"` or `"soft"` (Speed Soft Stir) |
| &nbsp;&nbsp;`time` | int **seconds** |
| &nbsp;&nbsp;`direction` | `"CCW"` — only for reverse |
| &nbsp;&nbsp;`temperature` | `{"value": "100", "unit": "C"}` — omit when unheated |
| Ingredient annotation | `{"type": "INGREDIENT", "data": {"description": "<exact text>"}, "position": {...}}` |
| `totalTime` / `prepTime` | int **seconds** (not ISO `PT25M`) |
| `yield` | `{"value": 2, "unitText": "portion"}` (key is `yield`; `recipeYield` is ignored) |
| `tool` | `["TM6"]` |

`position` offsets/lengths index into the step's `text`, so annotation spans
must exactly match the substring they cover.

## Disclaimer

Unofficial. Uses a private API that may change without notice. For personal use
with your own Cookidoo account.
