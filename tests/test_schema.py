"""Unit tests for the payload helpers (offsets, labels, validation)."""

import pytest

from cookidoo_uploader.schema import (Recipe, build_payload, fmt_time, step,
                                      tts, validate_payload)


def test_fmt_time_seconds_and_minutes():
    assert fmt_time(5) == "5 sec"
    assert fmt_time(59) == "59 sec"
    assert fmt_time(60) == "1 min"
    assert fmt_time(300) == "5 min"


def test_tts_unheated_omits_temperature():
    data, label = tts(5, 7)
    assert data == {"speed": "7", "time": 5}
    assert "temperature" not in data
    assert label == "5 sec/speed 7"


def test_tts_heated_reverse_soft():
    data, label = tts(600, "soft", temp=100, reverse=True)
    assert data["speed"] == "soft"
    assert data["direction"] == "CCW"
    assert data["temperature"] == {"value": "100", "unit": "C"}
    assert label == "10 min/100°C/speed soft stir/reverse"


def test_step_tts_label_offset_indexes_label():
    s = step("Saute the base.", settings=tts(300, 1, temp=120))
    ann = s["annotations"][0]
    off, ln = ann["position"]["offset"], ann["position"]["length"]
    assert s["text"][off:off + ln] == "5 min/120°C/speed 1"


def test_step_ingredient_spans_use_running_cursor():
    # The same word appears twice; each span must get its OWN offset, in order.
    s = step("Add butter, then more butter.",
             ingredient_spans=["butter", "butter"])
    offs = [a["position"]["offset"] for a in s["annotations"]]
    assert offs[0] < offs[1]
    assert offs == [4, 22]


def test_step_missing_span_raises():
    with pytest.raises(ValueError, match="not found"):
        step("Add salt.", ingredient_spans=["pepper"])


def test_step_without_annotations_has_no_key():
    s = step("Just stir.")
    assert "annotations" not in s


def test_build_payload_shape_and_tool():
    r = Recipe(name="X", ingredients=["1 egg"], instructions=[step("Crack 1 egg.")],
               total_time=600, prep_time=120, yield_value=2)
    p = build_payload(r, tool="TM7")
    assert p["ingredients"] == [{"type": "INGREDIENT", "text": "1 egg"}]
    assert p["tool"] == ["TM7"]
    assert p["totalTime"] == 600 and p["prepTime"] == 120
    assert p["yield"] == {"value": 2, "unitText": "portion"}


def test_validate_payload_passes_on_good_spans():
    r = Recipe(name="X", ingredients=["butter"],
               instructions=[step("Add butter.", ingredient_spans=["butter"])],
               total_time=1, prep_time=1, yield_value=1)
    validate_payload(build_payload(r))  # should not raise


def test_validate_payload_catches_tampered_offset():
    s = step("Add butter.", ingredient_spans=["butter"])
    s["annotations"][0]["position"]["offset"] = 0  # now points at "Add bu"
    payload = {"instructions": [s]}
    with pytest.raises(ValueError, match="INGREDIENT span covers"):
        validate_payload(payload)
