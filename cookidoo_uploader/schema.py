"""Recipe model + helpers that build the Cookidoo PATCH payload.

Schema (confirmed from captured browser PATCH traffic):
  - ingredients : [{"type":"INGREDIENT","text":<str>}]  (objects, not strings)
  - instructions: [{"type":"STEP","text":<str>,"annotations":[...]}]
  - TTS annotation: {"type":"TTS","data":{speed,time,[direction],[temperature]},
                     "position":{offset,length}}  -- span covers the settings label
        speed      : "1".."10" or "soft" (Speed Soft Stir)
        time       : int seconds
        direction  : "CCW" (only for reverse)
        temperature: {"value":"100","unit":"C"} (omit when unheated)
  - INGREDIENT auto-weigh: {"type":"INGREDIENT","data":{"description":<exact text>},position}
  - totalTime/prepTime : int SECONDS (not ISO "PT25M")
  - yield : key is "yield" {value, unitText:"portion"} (recipeYield is ignored)
  - tool : ["TM6"]
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .config import DEFAULT_TOOL


@dataclass
class Recipe:
    """A fully-built recipe, ready to turn into an upload payload."""

    name: str
    ingredients: List[str]
    instructions: List[dict]
    total_time: int            # seconds
    prep_time: int             # seconds
    yield_value: int
    yield_unit: str = "portion"


def fmt_time(secs: int) -> str:
    return f"{secs} sec" if secs < 60 else f"{secs // 60} min"


def tts(time: int, speed, temp=None, reverse: bool = False) -> Tuple[dict, str]:
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
    return data, "/".join(parts)


def step(main_text: str, settings: Optional[Tuple[dict, str]] = None,
         ingredient_spans: Optional[List[str]] = None) -> dict:
    """Assemble a STEP with optional TTS settings + INGREDIENT auto-weigh spans.

    ingredient_spans are exact substrings of main_text; each is located from a
    running cursor so a repeated phrase gets distinct, in-order offsets (rather
    than every span collapsing onto the first occurrence). Raises ValueError if
    a span isn't found at/after the cursor.
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


def build_payload(recipe: Recipe, tool: str = DEFAULT_TOOL) -> dict:
    """Turn a Recipe into the full create/PATCH payload for the given tool."""
    return {
        "name": recipe.name,
        "ingredients": [{"type": "INGREDIENT", "text": t} for t in recipe.ingredients],
        "instructions": recipe.instructions,
        "tool": [tool],
        "totalTime": recipe.total_time,
        "prepTime": recipe.prep_time,
        "yield": {"value": recipe.yield_value, "unitText": recipe.yield_unit},
    }


def validate_payload(payload: dict) -> None:
    """Safety net: assert every annotation position indexes its own substring.

    For INGREDIENT annotations the covered text must equal the description; for
    all annotations the span must be within the step text. Raises ValueError on
    the first problem so a malformed recipe fails before any network call.
    """
    for i, ins in enumerate(payload.get("instructions", [])):
        text = ins["text"]
        for a in ins.get("annotations", []):
            off = a["position"]["offset"]
            ln = a["position"]["length"]
            if off < 0 or off + ln > len(text):
                raise ValueError(
                    f"step {i}: annotation {a['type']} span [{off}:{off + ln}] "
                    f"out of range for text of length {len(text)}")
            if a["type"] == "INGREDIENT":
                covered = text[off:off + ln]
                want = a["data"]["description"]
                if covered != want:
                    raise ValueError(
                        f"step {i}: INGREDIENT span covers {covered!r}, "
                        f"expected {want!r}")
