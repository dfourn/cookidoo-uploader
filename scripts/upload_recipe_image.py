#!/usr/bin/env python3
"""
Attach an image to a Cookidoo created-recipe.

Cookidoo stores recipe photos on Cloudinary (cloud "vorwerk-users-gc") and the
`image` field on the recipe is read-only via PATCH UNLESS you go through the
signed upload flow, reverse-engineered from a captured browser HAR
(cookidoo_investigation/cookidoo.co.uk_Archive [26-06-24 ...].har):

  1. POST /created-recipes/en-GB/image/signature  (auth cookie)
       body {"timestamp": <unix>, "source": "uw", "custom_coordinates": "x,y,w,h"}
       -> {"signature": "<hex>"}   (api_secret stays server-side)
  2. POST https://api-eu.cloudinary.com/v1_1/vorwerk-users-gc/image/upload
       multipart: upload_preset, source, signature, timestamp, api_key,
                  custom_coordinates, file
       -> {"public_id": "...", "format": "jpg", "secure_url": "...", ...}
  3. PATCH /created-recipes/en-GB/{id}  (auth cookie)
       body {"image": "<public_id>.<format>", "isImageOwnedByUser": false}

The signature only covers {custom_coordinates, source, timestamp}; upload_preset
and api_key are sent unsigned (matches the captured request, which got 200).

Auth: reads _oauth2_proxy from $COOKIDOO_COOKIE, else from the browser via
get_cookidoo_cookie.py.

Usage:
    cookiput_venv/bin/python scripts/upload_recipe_image.py <RECIPE_ID> <IMAGE> [--dry-run]
"""

import argparse
import os
import sys
import time
import requests

DOMAIN = "https://cookidoo.co.uk"
LOCALE = "en-GB"
# These are public Cloudinary client identifiers (cloud name, API key, upload
# preset) — not secrets. The api_secret stays server-side and never appears
# here. They default to Cookidoo's production values but can be overridden via
# the environment.
CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "vorwerk-users-gc")
API_KEY = os.environ.get("CLOUDINARY_API_KEY", "993585863591145")
UPLOAD_PRESET = os.environ.get("CLOUDINARY_UPLOAD_PRESET", "prod-customer-recipe-signed")
CLOUD_URL = f"https://api-eu.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
HEADERS = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": UA}


def jpeg_size(path):
    """Return (width, height) for a JPEG by scanning the SOF marker."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:2] != b"\xff\xd8":
        raise ValueError(f"{path} is not a JPEG")
    i = 2
    while i < len(data) - 9:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            h = int.from_bytes(data[i + 5:i + 7], "big")
            w = int.from_bytes(data[i + 7:i + 9], "big")
            return w, h
        seg = int.from_bytes(data[i + 2:i + 4], "big")
        i += 2 + seg
    raise ValueError(f"could not find image dimensions in {path}")


SUPPORTED_FORMATS = "JPEG, PNG, WebP"


def detect_image(path):
    """Sniff magic bytes and return (mime_type, width, height).

    width/height may be None when we don't parse dimensions for the format
    (Cloudinary derives them from the uploaded file and returns them anyway).
    Raises ValueError for unsupported formats.
    """
    with open(path, "rb") as f:
        head = f.read(32)

    if head[:3] == b"\xff\xd8\xff":
        w, h = jpeg_size(path)
        return "image/jpeg", w, h
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        # IHDR width/height are big-endian 4-byte ints at offsets 16 and 20.
        w = int.from_bytes(head[16:20], "big")
        h = int.from_bytes(head[20:24], "big")
        return "image/png", w, h
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        # WebP dimension parsing is format-variant specific; let Cloudinary
        # derive them from the file.
        return "image/webp", None, None
    raise ValueError(
        f"{path}: unsupported image format (supported: {SUPPORTED_FORMATS})"
    )


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("recipe_id")
    ap.add_argument("image", help=f"path to an image ({SUPPORTED_FORMATS})")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    mime, w, h = detect_image(args.image)
    # custom_coordinates needs pixel dimensions; only send it when we know them
    # (and it must match between the signature request and the upload).
    coords = f"0,0,{w},{h}" if w is not None and h is not None else None
    ts = int(time.time())
    dims = f"{w}x{h}" if coords else "unknown size"
    print(f"image {args.image} ({mime}, {dims}) -> recipe {args.recipe_id}")

    sig_body = {"timestamp": ts, "source": "uw"}
    if coords:
        sig_body["custom_coordinates"] = coords

    if args.dry_run:
        print(f"[dry-run] would request signature for timestamp={ts}, "
              f"custom_coordinates={coords}, then Cloudinary upload + PATCH.")
        return

    cookie = get_cookie()
    s = requests.Session()
    s.cookies.set("_oauth2_proxy", cookie)

    # 1. signature
    r = s.post(f"{DOMAIN}/created-recipes/{LOCALE}/image/signature", headers=HEADERS,
               json=sig_body, timeout=20)
    if not r.ok:
        print("Signature request failed:", r.status_code, r.text[:500])
        sys.exit(1)
    try:
        signature = r.json()["signature"]
    except (ValueError, KeyError):
        print("Signature response was not the expected JSON:", r.text[:500])
        sys.exit(1)
    print("got signature")

    # 2. Cloudinary upload (multipart; no cookie, auth via api_key + signature)
    with open(args.image, "rb") as f:
        files = {"file": (os.path.basename(args.image), f, mime)}
        data = {
            "upload_preset": UPLOAD_PRESET,
            "source": "uw",
            "signature": signature,
            "timestamp": str(ts),
            "api_key": API_KEY,
        }
        if coords:
            data["custom_coordinates"] = coords
        cr = requests.post(CLOUD_URL, data=data, files=files,
                           headers={"User-Agent": UA}, timeout=60)
    if not cr.ok:
        print("Cloudinary upload failed:", cr.status_code, cr.text[:500])
        sys.exit(1)
    try:
        cj = cr.json()
        image_val = f"{cj['public_id']}.{cj['format']}"
    except (ValueError, KeyError):
        print("Cloudinary response was not the expected JSON:", cr.text[:500])
        sys.exit(1)
    print("uploaded:", cj.get("secure_url"))

    # 3. PATCH recipe
    pr = s.patch(f"{DOMAIN}/created-recipes/{LOCALE}/{args.recipe_id}", headers=HEADERS,
                 json={"image": image_val, "isImageOwnedByUser": False}, timeout=20)
    print(f"PATCH recipe image -> {pr.status_code}")
    if not pr.ok:
        print(pr.text[:500])
        sys.exit(1)

    # verify
    g = s.get(f"{DOMAIN}/created-recipes/{LOCALE}/{args.recipe_id}",
              headers={"Accept": "application/json", "User-Agent": UA}, timeout=20)
    if not g.ok:
        print("Could not re-fetch recipe to verify:", g.status_code, g.text[:500])
        return
    try:
        print("recipe image now:", g.json().get("recipeContent", {}).get("image"))
    except ValueError:
        print("Recipe verify response was not JSON:", g.text[:500])


if __name__ == "__main__":
    main()
