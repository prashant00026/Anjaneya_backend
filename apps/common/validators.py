"""File validators — size, image dimensions, real mime-type.

Mime detection uses `python-magic` (libmagic), which reads file bytes
instead of trusting the extension. On Windows the `python-magic-bin`
package supplies the bundled `libmagic-1.dll`.

Settings (with sane defaults — overridable via settings.py):
    MAX_IMAGE_SIZE_MB         (default 5)
    MAX_FLOOR_PLAN_SIZE_MB    (default 10)
    MIN_IMAGE_DIMENSIONS      (default (400, 300))
    MAX_IMAGE_DIMENSIONS      (default (8000, 8000))
    ALLOWED_IMAGE_MIME_TYPES  (default jpeg, png, webp)
    ALLOWED_FLOOR_PLAN_MIME_TYPES (default jpeg, png, webp, pdf)
"""

from __future__ import annotations

import os
import sys

# `python-magic-bin` ships libmagic.dll under `<site-packages>/magic/libmagic/`,
# which Windows' standard DLL search path does not include. Add that
# directory to the DLL search order BEFORE `import magic`. We locate the
# package via importlib.util.find_spec to avoid triggering the failing
# top-level import inside `magic/__init__.py`.
if sys.platform == "win32":
    import importlib.util

    _spec = importlib.util.find_spec("magic")
    if _spec is not None and _spec.origin:
        _bundled = os.path.join(os.path.dirname(_spec.origin), "libmagic")
        if os.path.isdir(_bundled):
            try:
                os.add_dll_directory(_bundled)
            except (AttributeError, OSError):
                pass
            os.environ["PATH"] = _bundled + os.pathsep + os.environ.get("PATH", "")

import magic  # noqa: E402
from django.conf import settings  # noqa: E402
from django.core.exceptions import ValidationError  # noqa: E402
from PIL import Image  # noqa: E402


_DEFAULT_IMAGE_MIMES = ("image/jpeg", "image/png", "image/webp")
_DEFAULT_FLOOR_PLAN_MIMES = (*_DEFAULT_IMAGE_MIMES, "application/pdf")


def _mb(value_bytes: int) -> float:
    return value_bytes / (1024 * 1024)


def _read_head(file_obj, n: int = 4096) -> bytes:
    """Read first `n` bytes for libmagic without exhausting the upload."""
    pos = file_obj.tell() if hasattr(file_obj, "tell") else 0
    try:
        file_obj.seek(0)
        head = file_obj.read(n)
    finally:
        try:
            file_obj.seek(pos)
        except Exception:
            pass
    return head


def validate_image_size(file_obj):
    """Reject images > MAX_IMAGE_SIZE_MB."""
    cap_mb = getattr(settings, "MAX_IMAGE_SIZE_MB", 5)
    if file_obj.size > cap_mb * 1024 * 1024:
        raise ValidationError(
            f"Image is {_mb(file_obj.size):.1f} MB; the limit is {cap_mb} MB.",
        )


def validate_image_dimensions(file_obj):
    """Reject images outside MIN_IMAGE_DIMENSIONS .. MAX_IMAGE_DIMENSIONS."""
    min_w, min_h = getattr(settings, "MIN_IMAGE_DIMENSIONS", (400, 300))
    max_w, max_h = getattr(settings, "MAX_IMAGE_DIMENSIONS", (8000, 8000))
    pos = file_obj.tell() if hasattr(file_obj, "tell") else 0
    try:
        file_obj.seek(0)
        with Image.open(file_obj) as img:
            w, h = img.size
    except Exception as e:
        raise ValidationError(f"Could not read image dimensions: {e}")
    finally:
        try:
            file_obj.seek(pos)
        except Exception:
            pass
    if w < min_w or h < min_h:
        raise ValidationError(
            f"Image {w}x{h} is smaller than the minimum {min_w}x{min_h}.",
        )
    if w > max_w or h > max_h:
        raise ValidationError(
            f"Image {w}x{h} exceeds the maximum {max_w}x{max_h}.",
        )


def _validate_mime(file_obj, allowed: tuple[str, ...], label: str):
    head = _read_head(file_obj)
    detected = magic.from_buffer(head, mime=True)
    if detected not in allowed:
        raise ValidationError(
            f"{label} mime type '{detected}' is not allowed. "
            f"Permitted: {', '.join(allowed)}.",
        )


def validate_image_mimetype(file_obj):
    """Real mime sniff (image/jpeg | image/png | image/webp)."""
    allowed = tuple(getattr(
        settings, "ALLOWED_IMAGE_MIME_TYPES", _DEFAULT_IMAGE_MIMES,
    ))
    _validate_mime(file_obj, allowed, "Image")


def validate_floor_plan(file_obj):
    """Image OR PDF, larger size ceiling (10 MB default)."""
    cap_mb = getattr(settings, "MAX_FLOOR_PLAN_SIZE_MB", 10)
    if file_obj.size > cap_mb * 1024 * 1024:
        raise ValidationError(
            f"File is {_mb(file_obj.size):.1f} MB; the limit is {cap_mb} MB.",
        )
    allowed = tuple(getattr(
        settings, "ALLOWED_FLOOR_PLAN_MIME_TYPES", _DEFAULT_FLOOR_PLAN_MIMES,
    ))
    _validate_mime(file_obj, allowed, "Floor plan")
