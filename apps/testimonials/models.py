from django.db import models

from common.upload_paths import testimonial_photo_path
from common.validators import validate_image_mimetype, validate_image_size


class Testimonial(models.Model):
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120, blank=True)
    content = models.TextField()
    photo = models.ImageField(
        upload_to=testimonial_photo_path, blank=True,
        validators=[validate_image_size, validate_image_mimetype],
    )

    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("display_order", "id")

    def __str__(self):
        return f"{self.name} ({self.role})" if self.role else self.name
