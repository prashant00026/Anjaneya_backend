from django.db import models
from django.utils.text import slugify

from common.upload_paths import team_photo_path
from common.validators import (
    validate_image_dimensions,
    validate_image_mimetype,
    validate_image_size,
)


class TeamMember(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    designation = models.CharField(max_length=120)
    bio = models.TextField(
        blank=True,
        help_text="Paragraphs separated by blank lines.",
    )
    photo = models.ImageField(
        upload_to=team_photo_path, blank=True,
        validators=[
            validate_image_size,
            validate_image_dimensions,
            validate_image_mimetype,
        ],
    )
    linkedin_url = models.URLField(blank=True)

    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("display_order", "id")

    def __str__(self):
        return f"{self.name} — {self.designation}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
