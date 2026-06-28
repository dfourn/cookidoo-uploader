"""Command-line entry point: `cookidoo <upload|image|cookie|login|list>`."""

import argparse
import json
import shlex
import sys

from . import recipes
from .auth import find_cookie, get_cookie
from .client import CookidooClient
from .config import DEFAULT_TOOL, TOOLS
from .errors import CookidooError
from .image import SUPPORTED_FORMATS, upload_image
from .schema import build_payload, validate_payload


def _warn_tm7(tool):
    if tool == "TM7":
        print("WARNING: --tool TM7 is untested/unverified against this private "
              "API (schema was reverse-engineered from TM6 traffic).",
              file=sys.stderr)


def cmd_list(args):
    for name in recipes.names():
        print(name)
    return 0


def cmd_upload(args):
    recipe = recipes.get(args.recipe)
    if recipe is None:
        print(f"Unknown recipe {args.recipe!r}. Available: "
              f"{', '.join(recipes.names())}", file=sys.stderr)
        return 2

    _warn_tm7(args.tool)
    payload = build_payload(recipe, tool=args.tool)
    validate_payload(payload)  # fail fast on any bad annotation span

    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        annotated = sum("annotations" in s for s in payload["instructions"])
        print(f"\n[dry-run] {len(payload['instructions'])} steps, "
              f"{annotated} with annotations.", file=sys.stderr)
        return 0

    client = CookidooClient(get_cookie())
    recipe_id = client.upload_recipe(payload, update_id=args.update_id)
    rc = client.verify(recipe_id)
    print(f"Uploaded recipe {recipe_id}")
    print("  name:", rc.get("name"))
    print("  ingredients:", len(rc.get("recipeIngredient", [])))
    print("  instructions:", len(rc.get("recipeInstructions", [])))
    print("  tool:", rc.get("tool"), "| totalTime:", rc.get("totalTime"),
          "| prepTime:", rc.get("prepTime"), "| yield:", rc.get("recipeYield"))
    print(f"\nView at: {client.domain}/created-recipes/{client.locale}/{recipe_id}")
    return 0


def cmd_image(args):
    client = CookidooClient(None if args.dry_run else get_cookie())
    if args.dry_run:
        from .image import detect_image
        mime, w, h = detect_image(args.image)
        dims = f"{w}x{h}" if w is not None and h is not None else "unknown size"
        print(f"[dry-run] {args.image} ({mime}, {dims}) -> recipe {args.recipe_id}; "
              "would request signature, upload to Cloudinary, then PATCH.")
        return 0
    image_val = upload_image(client, args.recipe_id, args.image)
    print(f"Set image {image_val} on recipe {args.recipe_id}")
    return 0


def cmd_cookie(args):
    res = find_cookie()
    if not res:
        raise CookidooError(
            "Could not find the Cookidoo `_oauth2_proxy` cookie in any browser. "
            "Make sure you are logged in to Cookidoo in Chrome, Safari, Firefox, "
            "Edge, or Brave, then run this again.")
    value, browser, domain = res
    if args.export:
        # shlex.quote escapes any shell special chars (including a literal '),
        # so `eval "$(cookidoo cookie --export)"` can't execute the value.
        print(f"export COOKIDOO_COOKIE={shlex.quote(value)}")
    else:
        print(f"Found `_oauth2_proxy` in {browser} (domain {domain}):", file=sys.stderr)
        print(value)
    return 0


def cmd_login(args):
    """Log in with stored credentials, cache the cookie, and print success."""
    if args.set_password:
        # Store password in the OS keychain via getpass.
        try:
            import keyring  # type: ignore[import]
        except ImportError:
            print(
                "ERROR: keyring is not installed. "
                "Install it with: pip install 'cookidoo-uploader[login]'",
                file=sys.stderr,
            )
            return 1

        import getpass

        from .userconfig import _KEYRING_SERVICE, load_config, resolve_email

        config = load_config()
        email = resolve_email(config=config)
        if not email:
            # Fall back to a prompt so the command is still usable without config.
            try:
                email = input("Cookidoo email: ").strip() or None
            except (KeyboardInterrupt, EOFError):
                print("\nAborted.", file=sys.stderr)
                return 1
        if not email:
            print(
                "ERROR: No email found. Set COOKIDOO_EMAIL or add "
                "`email` to ~/.config/cookidoo/config.toml",
                file=sys.stderr,
            )
            return 1

        try:
            password = getpass.getpass(f"Password for {email}: ")
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.", file=sys.stderr)
            return 1
        if not password:
            print("ERROR: Empty password — aborted.", file=sys.stderr)
            return 1

        keyring.set_password(_KEYRING_SERVICE, email, password)
        print(f"Password stored in keyring for {email}.")
        return 0

    # Perform login and cache the cookie.
    from .login import get_cookie_via_login

    result = get_cookie_via_login()
    if result is None:
        print(
            "No credentials configured. Add your email and password to "
            "~/.config/cookidoo/config.toml, set COOKIDOO_EMAIL/COOKIDOO_PASSWORD, "
            "or run `cookidoo login --set-password` to store in the keychain.",
            file=sys.stderr,
        )
        return 1

    print("Login successful. Cookie cached (valid for this session).")
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="cookidoo",
        description="Upload custom recipes (and photos) to Cookidoo for Thermomix.")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("list", help="list available built-in recipes")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("upload", help="upload a recipe")
    sp.add_argument("recipe", help="recipe slug (see `cookidoo list`)")
    sp.add_argument("--dry-run", action="store_true",
                    help="print the payload without uploading")
    sp.add_argument("--update-id", metavar="RECIPE_ID",
                    help="PATCH this existing recipe instead of creating a new one")
    sp.add_argument("--tool", choices=list(TOOLS), default=DEFAULT_TOOL,
                    help=f"Thermomix model (default {DEFAULT_TOOL}; TM7 is unverified)")
    sp.set_defaults(func=cmd_upload)

    sp = sub.add_parser("image", help="attach a photo to a recipe")
    sp.add_argument("recipe_id")
    sp.add_argument("image", help=f"path to an image ({SUPPORTED_FORMATS})")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_image)

    sp = sub.add_parser("cookie", help="read the auth cookie from your browser")
    sp.add_argument("--export", action="store_true",
                    help="print a shell `export COOKIDOO_COOKIE=...` line")
    sp.set_defaults(func=cmd_cookie)

    sp = sub.add_parser(
        "login",
        help="log in with stored credentials and cache the session cookie",
    )
    sp.add_argument(
        "--set-password",
        action="store_true",
        help="store your password in the OS keychain (requires keyring)",
    )
    sp.set_defaults(func=cmd_login)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except CookidooError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
