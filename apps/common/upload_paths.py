"""UUID-renaming upload-path callables.

Rules (per step 4 brief):
- Never trust the original filename.
- Always rename to a UUID.
- Preserve the original extension only after lowercasing.
- Use the parent FK id when available (gallery, floor-plan rows belong
  to a Project that already has a pk by the time the file is saved).
- For root-owner fields (Project.cover_image is set on the Project
  *itself*), fall back to the row's slug if pk is not yet assigned.
"""

from __future__ import annotations

import os
import uuid


_ALLOWED_EXTS = {
    ".jpg", ".jpeg", ".png", ".webp",
    ".pdf",  # for floor plans only — validators gate by mime, not ext
    ".svg",  # amenity icons / developer logos may be vector
}


def _safe_ext(filename: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    return ext if ext in _ALLOWED_EXTS else ""


def _uuid_name(filename: str) -> str:
    return f"{uuid.uuid4().hex}{_safe_ext(filename)}"


# -- Project ------------------------------------------------------------

def project_cover_path(instance, filename):
    """`projects/<id-or-slug>/cover/<uuid>.<ext>`.

    `instance` is the Project itself. On first save `pk` may be None;
    fall back to the slug which is always populated by Project.save().
    """
    key = instance.pk or instance.slug or "new"
    return f"projects/{key}/cover/{_uuid_name(filename)}"


def project_gallery_path(instance, filename):
    """`projects/<project_id>/gallery/<uuid>.<ext>`."""
    return f"projects/{instance.project_id}/gallery/{_uuid_name(filename)}"


def floor_plan_path(instance, filename):
    """`projects/<project_id>/floor_plans/<uuid>.<ext>`."""
    return f"projects/{instance.project_id}/floor_plans/{_uuid_name(filename)}"


# -- Catalog ------------------------------------------------------------

def developer_logo_path(instance, filename):
    return f"developers/{instance.slug or instance.pk or 'new'}/{_uuid_name(filename)}"


def amenity_icon_path(instance, filename):
    return f"amenities/{instance.slug or instance.pk or 'new'}/{_uuid_name(filename)}"


# -- Team / testimonials / CMS -----------------------------------------

def team_photo_path(instance, filename):
    return f"team/{instance.slug or instance.pk or 'new'}/{_uuid_name(filename)}"


def testimonial_photo_path(instance, filename):
    return f"testimonials/{instance.pk or 'new'}/{_uuid_name(filename)}"


def cms_hero_path(instance, filename):
    return f"cms/{instance.slug or instance.pk or 'new'}/{_uuid_name(filename)}"
