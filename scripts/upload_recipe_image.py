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
CLOUD_NAME = "vorwerk-users-gc"
API_KEY = "993585863591145"
UPLOAD_PRESET = "prod-customer-recipe-signed"
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
    ap.add_argument("image", help="path to a JPEG image")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    w, h = jpeg_size(args.image)
    coords = f"0,0,{w},{h}"
    ts = int(time.time())
    print(f"image {args.image} ({w}x{h}) -> recipe {args.recipe_id}")

    if args.dry_run:
        print(f"[dry-run] would request signature for timestamp={ts}, "
              f"custom_coordinates={coords}, then Cloudinary upload + PATCH.")
        return

    cookie = get_cookie()
    s = requests.Session()
    s.cookies.set("_oauth2_proxy", cookie)

    # 1. signature
    r = s.post(f"{DOMAIN}/created-recipes/{LOCALE}/image/signature", headers=HEADERS,
               json={"timestamp": ts, "source": "uw", "custom_coordinates": coords},
               timeout=20)
    r.raise_for_status()
    signature = r.json()["signature"]
    print("got signature")

    # 2. Cloudinary upload (multipart; no cookie, auth via api_key + signature)
    with open(args.image, "rb") as f:
        files = {"file": (os.path.basename(args.image), f, "image/jpeg")}
        data = {
            "upload_preset": UPLOAD_PRESET,
            "source": "uw",
            "signature": signature,
            "timestamp": str(ts),
            "api_key": API_KEY,
            "custom_coordinates": coords,
        }
        cr = requests.post(CLOUD_URL, data=data, files=files,
                           headers={"User-Agent": UA}, timeout=60)
    if not cr.ok:
        print("Cloudinary upload failed:", cr.status_code, cr.text[:500])
        sys.exit(1)
    cj = cr.json()
    image_val = f"{cj['public_id']}.{cj['format']}"
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
    print("recipe image now:", g.json().get("recipeContent", {}).get("image"))


if __name__ == "__main__":
    main()
