"""Uploaded photos: validate, clean, resize, store.

Every upload is decoded and re-encoded, never stored as sent:
- **Metadata is dropped.** Phone photos carry EXIF GPS coordinates. A
  "private" pin whose photo is public (or later shared) would leak the
  exact spot through its metadata; re-encoding without EXIF removes that,
  along with camera serial numbers and the rest.
- **Only real images survive.** Content type and extension are the
  client's claims; decoding is the check. A file that isn't a JPEG, PNG
  or WebP image Pillow can fully decode is rejected, so nothing else is
  ever served back from our media URLs.
- **Decompression bombs are refused** by a pixel ceiling before decoding.
- Orientation is applied (EXIF rotate) before the tag is dropped, so
  portrait photos don't come out sideways.

Storage is a small interface (`MediaStore`) with a local-folder
implementation for the demo; object storage (S3 / R2) is a second
implementation, not a rewrite.
"""
from __future__ import annotations

import io
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings

# MPO is how Pillow reports the multi-picture JPEGs many phone cameras
# write; only the first (primary) frame is kept.
ALLOWED_FORMATS = {"JPEG", "MPO", "PNG", "WEBP"}
MAX_PIXELS = 40_000_000  # ~ a 48 MP phone photo downsampled; bombs are far larger
FULL_MAX_EDGE = 2048
THUMB_MAX_EDGE = 640

Image.MAX_IMAGE_PIXELS = MAX_PIXELS


class PhotoRejected(Exception):
    """The upload isn't an acceptable photo. Message is safe to show."""


@dataclass(frozen=True)
class CleanPhoto:
    full: bytes
    thumb: bytes
    width: int
    height: int


def _flatten(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    return img.convert("RGB")


def _jpeg(img: Image.Image, max_edge: int, quality: int) -> tuple[bytes, int, int]:
    copy = img.copy()
    copy.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    # No exif= argument: the new file carries no metadata at all.
    copy.save(out, format="JPEG", quality=quality, optimize=True, progressive=True)
    return out.getvalue(), copy.width, copy.height


def clean_photo(data: bytes) -> CleanPhoto:
    max_bytes = get_settings().max_photo_bytes
    if len(data) == 0:
        raise PhotoRejected("That file is empty.")
    if len(data) > max_bytes:
        raise PhotoRejected(f"Photos can be up to {max_bytes // (1024 * 1024)} MB.")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format
            if fmt not in ALLOWED_FORMATS:
                raise PhotoRejected("Upload a JPEG, PNG or WebP photo.")
            if probe.width * probe.height > MAX_PIXELS:
                raise PhotoRejected("That image is too large.")
            probe.verify()  # structural check; the image must be reopened after
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            img = ImageOps.exif_transpose(img)
            img = _flatten(img)
    except PhotoRejected:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError, ValueError) as exc:
        raise PhotoRejected("That file isn't a photo we can read.") from exc

    full, w, h = _jpeg(img, FULL_MAX_EDGE, 85)
    thumb, _, _ = _jpeg(img, THUMB_MAX_EDGE, 78)
    return CleanPhoto(full=full, thumb=thumb, width=w, height=h)


class MediaStore(Protocol):
    def save(self, key: str, full: bytes, thumb: bytes) -> None: ...
    def path(self, key: str, variant: str) -> Path | None: ...
    def delete(self, key: str) -> None: ...


class LocalMediaStore:
    """Files under MEDIA_ROOT: <key>.jpg and <key>_thumb.jpg.

    Never exposed as a static folder — media.py's API route checks who may
    see a photo (a private pin's photos are its owner's) before serving it.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def _file(self, key: str, variant: str) -> Path:
        suffix = "_thumb.jpg" if variant == "thumb" else ".jpg"
        p = (self.root / f"{key}{suffix}").resolve()
        # Keys are generated server-side, but a path that escapes the root
        # must be impossible regardless of where a key came from.
        if self.root not in p.parents:
            raise ValueError("media key escapes the media root")
        return p

    def save(self, key: str, full: bytes, thumb: bytes) -> None:
        for variant, data in (("full", full), ("thumb", thumb)):
            target = self._file(key, variant)
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(".tmp")
            tmp.write_bytes(data)
            os.replace(tmp, target)  # atomic: never serve a half-written file

    def path(self, key: str, variant: str) -> Path | None:
        p = self._file(key, variant)
        return p if p.is_file() else None

    def delete(self, key: str) -> None:
        for variant in ("full", "thumb"):
            try:
                self._file(key, variant).unlink(missing_ok=True)
            except OSError:
                pass  # a stray file is harmless; failing a delete isn't


def new_key(pin_id: int) -> str:
    return f"pins/{pin_id}/{secrets.token_hex(12)}"


def get_store() -> MediaStore:
    return LocalMediaStore(get_settings().media_root)
