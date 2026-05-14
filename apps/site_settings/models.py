from django.core.exceptions import ValidationError
from django.db import models

from common.upload_paths import cms_hero_path
from common.validators import (
    validate_image_dimensions,
    validate_image_mimetype,
    validate_image_size,
)


class SiteSettings(models.Model):
    """Singleton config row — exactly one record, pk forced to 1."""

    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    whatsapp_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)

    hero_stat_clients = models.CharField(max_length=20, default="98+")
    hero_stat_clients_label = models.CharField(
        max_length=120,
        default="Happy clients, countless smiles delivered",
    )
    hero_stat_value = models.CharField(max_length=20, default="100Cr+")
    hero_stat_value_label = models.CharField(
        max_length=120,
        default="Property value managed with excellence",
    )

    copyright_year = models.PositiveIntegerField(default=2026)

    class Meta:
        verbose_name = "site settings"
        verbose_name_plural = "site settings"

    def __str__(self):
        return "Site settings"

    def clean(self):
        if SiteSettings.objects.exclude(pk=self.pk).exists():
            raise ValidationError("Only one SiteSettings row is allowed.")

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "SiteSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class CmsPage(models.Model):
    """Lightweight CMS page (About / Privacy / Terms / Disclaimer)."""

    slug = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=160)
    body = models.TextField(blank=True, help_text="Markdown.")
    hero_image = models.ImageField(
        upload_to=cms_hero_path, blank=True,
        validators=[
            validate_image_size,
            validate_image_dimensions,
            validate_image_mimetype,
        ],
    )
    is_published = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("slug",)

    def __str__(self):
        return self.title
