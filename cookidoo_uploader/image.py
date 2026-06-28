"""Attach a photo to a created-recipe via Cookidoo's Cloudinary signed-upload flow.

  1. POST /created-recipes/{locale}/image/signature  (auth cookie)
       body {"timestamp": <unix>, "source": "uw", [custom_coordinates]}
       -> {"signature": "<hex>"}   (api_secret stays server-side)
  2. POST https://api-eu.cloudinary.com/v1_1/{cloud}/image/upload
       multipart: upload_preset, source, signature, timestamp, api_key,
                  [custom_coordinates], file  -> {"public_id","format","secure_url",...}
  3. PATCH /created-recipes/{locale}/{id}
       body {"image": "<public_id>.<format>", "isImageOwnedByUser": false}

The signature only covers {custom_coordinates, source, timestamp}; upload_preset
and api_key are sent unsigned (matches the captured request that got 200).
"""

import os
import time

import requests

from .config import (CLOUD_URL, CLOUDINARY_API_KEY, HEADERS, UA, UPLOAD_PRESET)
from .errors import CookidooError

SUPPORTED_FORMATS = "JPEG, PNG, WebP"


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


def detect_image(path):
    """Sniff magic bytes and return (mime_type, width, height).

    width/height may be None when we don't parse dimensions for the format
    (Cloudinary derives them from the file anyway). Raises ValueError for
    unsupported formats.
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
        # WebP dimension parsing is variant-specific; let Cloudinary derive them.
        return "image/webp", None, None
    raise ValueError(
        f"{path}: unsupported image format (supported: {SUPPORTED_FORMATS})")


def upload_image(client, recipe_id, image_path, dry_run=False):
    """Run the 3-step image flow against an authenticated CookidooClient.

    Returns the image value (public_id.format) set on the recipe, or None for a
    dry run. Raises CookidooError on any API failure.
    """
    mime, w, h = detect_image(image_path)
    coords = f"0,0,{w},{h}" if w is not None and h is not None else None
    ts = int(time.time())

    sig_body = {"timestamp": ts, "source": "uw"}
    if coords:
        sig_body["custom_coordinates"] = coords

    if dry_run:
        return None

    s = client.session
    # 1. signature
    r = s.post(f"{client.domain}/created-recipes/{client.locale}/image/signature",
               headers=HEADERS, json=sig_body, timeout=20)
    if not r.ok:
        raise CookidooError(f"signature request failed ({r.status_code}): {r.text[:500]}")
    try:
        signature = r.json()["signature"]
    except (ValueError, KeyError):
        raise CookidooError(f"signature response was not the expected JSON: {r.text[:500]}")

    # 2. Cloudinary upload (multipart; auth via api_key + signature, no cookie)
    with open(image_path, "rb") as f:
        files = {"file": (os.path.basename(image_path), f, mime)}
        data = {
            "upload_preset": UPLOAD_PRESET,
            "source": "uw",
            "signature": signature,
            "timestamp": str(ts),
            "api_key": CLOUDINARY_API_KEY,
        }
        if coords:
            data["custom_coordinates"] = coords
        cr = requests.post(CLOUD_URL, data=data, files=files,
                           headers={"User-Agent": UA}, timeout=60)
    if not cr.ok:
        raise CookidooError(f"Cloudinary upload failed ({cr.status_code}): {cr.text[:500]}")
    try:
        cj = cr.json()
        image_val = f"{cj['public_id']}.{cj['format']}"
    except (ValueError, KeyError):
        raise CookidooError(f"Cloudinary response was not the expected JSON: {cr.text[:500]}")

    # 3. PATCH recipe
    client.patch(recipe_id, {"image": image_val, "isImageOwnedByUser": False},
                 "PATCH recipe image")
    return image_val
