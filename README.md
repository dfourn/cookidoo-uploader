# Cookidoo Uploader

Upload your own recipes to [Cookidoo](https://cookidoo.co.uk) — Thermomix's
official recipe platform — as **Created Recipes** with fully programmable
guided-cooking steps for the **Thermomix TM6** (and, experimentally, the
**TM7**). Each step can carry the time / temperature / speed / reverse settings
that drive the machine, plus auto-weigh ingredient annotations, so your own
Thermomix recipes run as guided cooking just like Cookidoo's own.

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
pip install -e .          # installs the `cookidoo` command
```

This installs the `cookidoo_uploader` package and a `cookidoo` console command.

## Authentication

The tool reads the `_oauth2_proxy` cookie in one of two ways:

- **Automatic** — `cookidoo cookie` reads it straight from your installed
  browser (Chrome/Safari/Firefox/Edge/Brave). On macOS the first run triggers a
  one-time Keychain prompt to decrypt the browser cookie store. Export it into
  your shell with:

  ```bash
  eval "$(cookidoo cookie --export)"
  ```

- **Manual** — set it yourself if you'd rather not touch the browser store:

  ```bash
  export COOKIDOO_COOKIE='<value of the _oauth2_proxy cookie>'
  ```

  Get the value from DevTools → Application → Cookies → `_oauth2_proxy` while
  logged in to Cookidoo. It expires periodically; log out/in to refresh.

> The cookie is a live session credential. Never commit it — `.har` files and
> `.env` are gitignored for this reason.

A planned **config-file auto-login** (email/password → cookie, no browser
extraction) is designed in [`docs/auto-login-plan.md`](docs/auto-login-plan.md).

## Usage

List the built-in recipes:

```bash
cookidoo list
```

Preview a recipe's JSON payload without sending anything:

```bash
cookidoo upload chicken-tikka-masala --dry-run
```

Create it live in your Cookidoo account:

```bash
cookidoo upload chicken-tikka-masala
```

Re-run against an existing recipe instead of creating a new one:

```bash
cookidoo upload chicken-tikka-masala --update-id <RECIPE_ID>
```

### Choosing the Thermomix model

`cookidoo upload` takes a `--tool {TM6,TM7}` flag (default `TM6`) that sets the
`tool` value sent to the API:

```bash
cookidoo upload chicken-tikka-masala --tool TM7
```

> **TM7 support is experimental and untested.** The API schema — including the
> `tool` value — was reverse-engineered from captured **TM6** browser traffic,
> and `TM6` is the only value confirmed to work. `TM7` *should* behave the same
> way, but it has not been verified against the live API: the endpoint may
> reject the `tool` enum, and the TM7's different hardware (temperature range,
> speed settings) means guided steps could behave differently. If you have a
> TM7, feedback on what works is very welcome.

Attach a photo to a recipe:

```bash
cookidoo image <RECIPE_ID> path/to/photo.jpg   # JPEG, PNG, or WebP
```

The [`example/`](example/) folder holds plain-Markdown source templates for the
recipes — a readable starting point for writing your own. Note these are
human-readable references only: the recipe modules do **not** parse them, they
each encode their recipe data directly in Python.

## Writing a new recipe

Add a module under `cookidoo_uploader/recipes/` (copy an existing one) that
defines a `RECIPE`, then register it in `cookidoo_uploader/recipes/__init__.py`.
A recipe needs three things:

- `INGREDIENTS` — list of strings. Each becomes
  `{"type": "INGREDIENT", "text": ...}`.
- `INSTRUCTIONS` — one `step(...)` per guided step, using the helpers from
  `cookidoo_uploader.schema`:
  - `tts(time, speed, temp=None, reverse=False)` — attaches TM6 settings. A
    human-readable label (`5 min/100°C/speed 1/reverse`) is appended to the
    step text and the matching span is annotated for guided cooking.
  - `step(text, settings=tts(...), ingredient_spans=[...])` — `ingredient_spans`
    are exact substrings of the step text that get tagged for auto-weighing
    (located in order, so a repeated phrase still gets distinct offsets).
- A `Recipe(...)` carrying `name`, `total_time`, `prep_time` (seconds) and
  `yield_value`. The `tool` value (`TM6` by default, or `TM7` via `--tool`) is
  applied at upload time.

## Development

```bash
pip install -e ".[dev]"
pytest          # offline unit/golden tests (no creds, no network)
ruff check .
```

The tests cover the annotation-offset maths, payload schema, the HTTP client
(with a mocked session), and image content-type detection — none of which need
a Cookidoo account.

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
| `tool` | `["TM6"]` confirmed from captured traffic (the only value verified to work). `["TM7"]` is selectable via `--tool TM7` but is unverified against the live API. |

`position` offsets/lengths index into the step's `text`, so annotation spans
must exactly match the substring they cover.

## Disclaimer

Unofficial. Uses a private API that may change without notice. For personal use
with your own Cookidoo account.
