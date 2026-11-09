"""Shrink uploaded photos before they are stored.

A phone photo (3–10 MB, often HEIC) becomes a ~300–600 KB JPEG, max 2000 px,
rotated correctly and without GPS/EXIF data.  PDFs and anything Pillow cannot
read are stored unchanged.  Pillow is optional: without it nothing breaks.
"""
import io
import logging
import os

from django.conf import settings
from django.core.files.base import ContentFile

log = logging.getLogger(__name__)

try:
    from PIL import Image, ImageOps
    try:
        from pillow_heif import register_heif_opener  # iPhone HEIC support
        register_heif_opener()
    except ImportError:
        pass
    HAS_PIL = True
except ImportError:  # pragma: no cover
    HAS_PIL = False

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}


def compress(upload):
    """Return (django File, filename) ready for FileField.save()."""
    name = upload.name
    base, ext = os.path.splitext(name)
    if not HAS_PIL or ext.lower() not in IMAGE_EXT:
        return upload, name
    try:
        upload.seek(0)
        img = Image.open(upload)
        img = ImageOps.exif_transpose(img)  # respect phone orientation
        if img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", img.size, "white")
            img = img.convert("RGBA")
            bg.paste(img, mask=img.split()[-1])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        side = settings.IMAGE_MAX_SIDE
        img.thumbnail((side, side), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=settings.IMAGE_QUALITY, optimize=True, progressive=True)
        data = buf.getvalue()
        if ext.lower() in (".jpg", ".jpeg") and len(data) >= upload.size:
            upload.seek(0)
            return upload, name  # original was already small
        return ContentFile(data), f"{base[:100]}.jpg"
    except Exception:
        log.warning("Could not compress %s, storing original", name, exc_info=True)
        upload.seek(0)
        return upload, name
