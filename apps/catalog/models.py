from django.db import models
from django.utils.text import slugify

from common.upload_paths import amenity_icon_path, developer_logo_path
from common.validators import validate_image_mimetype, validate_image_size


class _Named(models.Model):
    """Common shape: name + auto slug + ordering + active flag."""

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        ordering = ("display_order", "name")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class City(_Named):
    class Meta(_Named.Meta):
        verbose_name_plural = "cities"


class Category(_Named):
    description = models.TextField(blank=True)

    class Meta(_Named.Meta):
        verbose_name_plural = "categories"


class Developer(_Named):
    description = models.TextField(blank=True)
    logo = models.ImageField(
        upload_to=developer_logo_path, blank=True,
        validators=[validate_image_size, validate_image_mimetype],
    )
    website = models.URLField(blank=True)


class Amenity(_Named):
    # Icons are small (often SVG) so we skip dimension validation here
    # and only enforce a size cap. Mime sniffing rejects executables
    # masquerading as `.svg`/`.png`.
    icon = models.ImageField(
        upload_to=amenity_icon_path, blank=True,
        validators=[validate_image_size, validate_image_mimetype],
    )

    class Meta(_Named.Meta):
        verbose_name_plural = "amenities"
