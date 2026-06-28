"""Magic-byte content-type detection tests (no network)."""

import pytest

from cookidoo_uploader.image import detect_image

# Minimal valid-enough headers for detect_image / jpeg_size.
JPEG = (b"\xff\xd8"                      # SOI
        b"\xff\xc0\x00\x11\x08"          # SOF0, length, precision
        b"\x00\x10\x00\x20"              # height=16, width=32
        b"\x00\x00\x00")
PNG = (b"\x89PNG\r\n\x1a\n"             # signature (8)
       b"\x00\x00\x00\x0dIHDR"          # length + IHDR (bytes 8-15)
       b"\x00\x00\x00\x40"              # width=64  (bytes 16-19)
       b"\x00\x00\x00\x20")             # height=32 (bytes 20-23)
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 "
GIF = b"GIF89a\x00\x00"


def _write(tmp_path, name, data):
    p = tmp_path / name
    p.write_bytes(data)
    return str(p)


def test_detect_jpeg(tmp_path):
    assert detect_image(_write(tmp_path, "a.jpg", JPEG)) == ("image/jpeg", 32, 16)


def test_detect_png(tmp_path):
    assert detect_image(_write(tmp_path, "a.png", PNG)) == ("image/png", 64, 32)


def test_detect_webp_defers_dimensions(tmp_path):
    assert detect_image(_write(tmp_path, "a.webp", WEBP)) == ("image/webp", None, None)


def test_unsupported_format_raises(tmp_path):
    with pytest.raises(ValueError, match="unsupported image format"):
        detect_image(_write(tmp_path, "a.gif", GIF))
