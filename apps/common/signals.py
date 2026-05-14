"""Shared `post_delete` cleanup helper.

When a row owning a `FileField` / `ImageField` is deleted, also delete
the underlying file from storage. imagekit-generated derivatives are
deleted via their own `source.delete()` because they're keyed off the
source file path.
"""

from __future__ import annotations

from django.db.models.fields.files import FieldFile


def delete_file_fields(instance) -> None:
    """Iterate every FieldFile on `instance` and delete the file."""
    for field in instance._meta.get_fields():
        # We only care about concrete File/Image fields.
        if not getattr(field, "concrete", False):
            continue
        attr = getattr(instance, field.name, None)
        if isinstance(attr, FieldFile) and attr.name:
            try:
                attr.delete(save=False)
            except Exception:
                # Storage may have already cleared the file (e.g. when the
                # row was bulk-replaced). Swallow; we're already in delete.
                pass
