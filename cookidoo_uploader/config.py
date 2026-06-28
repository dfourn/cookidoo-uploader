"""Endpoints, headers, and (public) Cloudinary identifiers, all env-overridable."""

import os

DOMAIN = os.environ.get("COOKIDOO_DOMAIN", "https://cookidoo.co.uk")
LOCALE = os.environ.get("COOKIDOO_LOCALE", "en-GB")

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": UA,
}

# Public Cloudinary client identifiers (cloud name, API key, upload preset) —
# NOT secrets. The api_secret stays server-side and never appears here. These
# default to Cookidoo's production values but can be overridden via the env.
CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "vorwerk-users-gc")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "993585863591145")
UPLOAD_PRESET = os.environ.get("CLOUDINARY_UPLOAD_PRESET", "prod-customer-recipe-signed")
CLOUD_URL = f"https://api-eu.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload"

# Tool values the CLI exposes. TM6 is confirmed from captured traffic; TM7 is
# selectable but UNVERIFIED against the private API (see README).
TOOLS = ("TM6", "TM7")
DEFAULT_TOOL = "TM6"
