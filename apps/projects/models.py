from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill, ResizeToFit
from simple_history.models import HistoricalRecords

from common.upload_paths import (
    floor_plan_path,
    project_cover_path,
    project_gallery_path,
)

# Backwards-compat shims so 0001_initial.py (which references the old
# names) can still resolve them at load time. New code should import
# from `common.upload_paths`.
_project_cover_path = project_cover_path
_project_gallery_path = project_gallery_path
from common.validators import (
    validate_floor_plan,
    validate_image_dimensions,
    validate_image_mimetype,
    validate_image_size,
)


_IMAGE_VALIDATORS = (
    validate_image_size,
    validate_image_dimensions,
    validate_image_mimetype,
)


class Project(models.Model):
    class Status(models.TextChoices):
        NEW_LAUNCH = "new_launch", "New Launch"
        UNDER_CONSTRUCTION = "under_construction", "Under Construction"
        READY_TO_MOVE = "ready_to_move", "Ready to Move"
        SOLD_OUT = "sold_out", "Sold Out"

    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)

    category = models.ForeignKey(
        "catalog.Category", on_delete=models.PROTECT, related_name="projects",
    )
    city = models.ForeignKey(
        "catalog.City", on_delete=models.PROTECT, related_name="projects",
    )
    locality = models.CharField(max_length=120, blank=True)
    developer = models.ForeignKey(
        "catalog.Developer",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="projects",
    )

    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.UNDER_CONSTRUCTION,
    )
    property_type = models.CharField(max_length=120, blank=True)
    tagline = models.CharField(max_length=240, blank=True)
    description = models.TextField(blank=True)

    price_starting_lacs = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Machine-sortable starting price in lakhs (₹).",
    )
    price_display = models.CharField(
        max_length=60, blank=True,
        help_text="Free-text price label shown on the site, e.g. '80 Lacs*'.",
    )
    size_display = models.CharField(
        max_length=80, blank=True,
        help_text="e.g. '360 Sq.Ft. onwards'.",
    )
    rera_number = models.CharField(max_length=60, blank=True)
    map_embed_url = models.URLField(
        blank=True, max_length=600,
        help_text="Google Maps iframe `src` URL.",
    )

    cover_image = models.ImageField(
        upload_to=project_cover_path, blank=True,
        validators=list(_IMAGE_VALIDATORS),
    )
    cover_thumbnail = ImageSpecField(
        source="cover_image",
        processors=[ResizeToFill(400, 300)],
        format="JPEG",
        options={"quality": 80},
    )
    cover_medium = ImageSpecField(
        source="cover_image",
        processors=[ResizeToFit(800, 600)],
        format="JPEG",
        options={"quality": 85},
    )
    cover_large = ImageSpecField(
        source="cover_image",
        processors=[ResizeToFit(1600, 1200)],
        format="JPEG",
        options={"quality": 90},
    )

    amenities = models.ManyToManyField(
        "catalog.Amenity", blank=True, related_name="projects",
    )

    is_featured = models.BooleanField(default=False)
    featured_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Step 8: simple-history adds a HistoricalProject row on every
    # save/delete, surfaced in admin's History tab with diff + actor.
    history = HistoricalRecords()

    class Meta:
        ordering = ("-published_at", "-id")
        indexes = [
            models.Index(fields=("is_published", "is_featured")),
            models.Index(fields=("city", "category")),
            # Step 5: support sort by Newest (default) and by Price.
            models.Index(fields=("-published_at",)),
            models.Index(fields=("price_starting_lacs",)),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:180]
        if self.is_published and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


class ProjectImageManager(models.Manager):
    def primary(self):
        """Return the flagged primary, or fall back to the first by order."""
        return self.filter(is_primary=True).first() or self.order_by("display_order", "id").first()


class ProjectImage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(
        upload_to=project_gallery_path,
        validators=list(_IMAGE_VALIDATORS),
    )
    thumbnail = ImageSpecField(
        source="image",
        processors=[ResizeToFill(400, 300)],
        format="JPEG",
        options={"quality": 80},
    )
    medium = ImageSpecField(
        source="image",
        processors=[ResizeToFit(800, 600)],
        format="JPEG",
        options={"quality": 85},
    )
    large = ImageSpecField(
        source="image",
        processors=[ResizeToFit(1600, 1200)],
        format="JPEG",
        options={"quality": 90},
    )

    caption = models.CharField(max_length=200, blank=True)
    alt_text = models.CharField(
        max_length=200, blank=True,
        help_text="Used by the frontend `alt` attribute (a11y + SEO).",
    )
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_primary = models.BooleanField(default=False)

    objects = ProjectImageManager()

    class Meta:
        ordering = ("display_order", "id")

    def __str__(self):
        return f"{self.project.title} · image #{self.pk}"

    def save(self, *args, **kwargs):
        # Single-primary invariant per project.
        if self.is_primary and self.project_id:
            with transaction.atomic():
                ProjectImage.objects.filter(
                    project_id=self.project_id, is_primary=True,
                ).exclude(pk=self.pk).update(is_primary=False)
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)


class FloorPlan(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="floor_plans")
    file = models.FileField(
        upload_to=floor_plan_path,
        validators=[validate_floor_plan],
        help_text="JPEG / PNG / WEBP / PDF, up to 10 MB.",
    )
    label = models.CharField(
        max_length=80, blank=True,
        help_text="e.g. 'Ground Floor', '2 BHK Type A'.",
    )
    caption = models.CharField(max_length=200, blank=True)
    alt_text = models.CharField(max_length=200, blank=True)
    display_order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ("display_order", "id")

    def __str__(self):
        return f"{self.project.title} · {self.label or 'plan #' + str(self.pk)}"


class ProjectHighlight(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="highlights")
    text = models.CharField(max_length=200)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "id")

    def __str__(self):
        return f"{self.project.title} · {self.text[:40]}"


class ProjectStat(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="stats")
    label = models.CharField(
        max_length=60,
        help_text="e.g. 'Property status', 'Price Starts from', 'Sizes', 'Developer', 'Property Type'.",
    )
    value = models.CharField(max_length=120)
    icon_key = models.CharField(
        max_length=40, blank=True,
        help_text="String identifier the frontend maps to an icon asset.",
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "id")

    def __str__(self):
        return f"{self.project.title} · {self.label}: {self.value}"
