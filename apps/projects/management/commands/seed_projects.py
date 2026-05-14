"""Seed the 8 projects shipped in the live frontend bundle.

Three are marked featured (matches the home-page "Featured Properties"
row). Only CRC The Flagship has rich detail (description / stats /
highlights / amenities) per the bundle — the other 7 get the short
shape (title / category / city / locality / tagline).
"""

import io
import random

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from catalog.models import Amenity, Category, City, Developer
from projects.models import (
    FloorPlan,
    Project,
    ProjectHighlight,
    ProjectImage,
    ProjectStat,
)


def _generate_placeholder(title: str, label: str, *, size=(1600, 1000), color=None) -> bytes:
    """Solid-color JPEG with project title + label text overlay."""
    if color is None:
        # Deterministic-ish palette so re-runs produce similar output.
        rng = random.Random(title)
        color = (rng.randint(60, 200), rng.randint(60, 200), rng.randint(60, 200))
    img = Image.new("RGB", size, color=color)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 72)
        small = ImageFont.truetype("arial.ttf", 40)
    except Exception:
        font = ImageFont.load_default()
        small = font
    draw.text((60, 60), title, fill="white", font=font)
    draw.text((60, 160), label, fill="white", font=small)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _generate_floor_plan(title: str) -> bytes:
    """Simple line-art rectangle as a floor plan placeholder."""
    img = Image.new("RGB", (1600, 1200), color="white")
    draw = ImageDraw.Draw(img)
    draw.rectangle((100, 100, 1500, 1100), outline="black", width=4)
    draw.line((800, 100, 800, 1100), fill="black", width=2)
    draw.line((100, 600, 1500, 600), fill="black", width=2)
    try:
        font = ImageFont.truetype("arial.ttf", 56)
    except Exception:
        font = ImageFont.load_default()
    draw.text((140, 140), f"{title} — Floor Plan (placeholder)", fill="black", font=font)
    draw.text((220, 700), "Living", fill="gray", font=font)
    draw.text((900, 700), "Bedroom", fill="gray", font=font)
    draw.text((220, 220), "Entry", fill="gray", font=font)
    draw.text((900, 220), "Kitchen", fill="gray", font=font)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


# (title, category_name, city_name, locality, tagline, is_featured, featured_order, developer_name)
PROJECTS = [
    ("CRC The Flagship",     "Commercial",  "Noida",          "Sector-140A, Noida",       "Premium Retail Shops & Commercial Spaces",       True,  1, "CRC Group"),
    ("Godrej Tropical Isle", "Residential", "Noida",          "Sector-146, Noida",        "Ultra-Luxury Apartments with Private Decks",     True,  2, "Godrej Properties"),
    ("Ace Terra",            "Residential", "Noida",          "Yamuna Expressway, Noida", "Modern Lifestyle Apartments in Gated Community", True,  3, "Ace Group"),
    ("Sunrise Residency",    "Residential", "Gurugram",       "Sector-45, Gurgaon",       "Modern Apartments with Green Spaces",            False, 0, "Sunrise Developers"),
    ("Group 108",            "Commercial",  "Noida",          "Sector-62, Noida",         "Warehouse and Distribution Centers",             False, 0, "Group 108"),
    ("Harmony Heights",      "Residential", "Faridabad",      "Sector-21, Faridabad",     "Integrated Living, Shopping, and Office Spaces", False, 0, "Harmony Builders"),
    ("Eldeco Echo of Eden",  "Residential", "Ghaziabad",      "Sector-17, Ghaziabad",     "State-of-the-Art School Campus",                 False, 0, "Eldeco"),
]


CRC_DESCRIPTION = (
    "CRC The Flagship is an upcoming commercial development located in "
    "Sector-140A, Noida, one of the fastest-growing business hubs along "
    "the Noida Expressway. Developed by CRC Group, the project is "
    "strategically positioned on a prime corner plot, offering excellent "
    "visibility and seamless accessibility. Designed to cater to modern "
    "business needs, it features premium retail shops, serviced suites, "
    "office spaces, and a vibrant food court, creating a dynamic "
    "commercial ecosystem.\n\n"
    "The development focuses on high footfall and strong investment "
    "potential, making it ideal for investors and business owners. With "
    "modern infrastructure, multiple entry and exit points, and a "
    "thoughtfully planned layout, it ensures convenience for both "
    "visitors and occupants. CRC The Flagship integrates lifestyle and "
    "business with amenities such as a sky lounge, retail entertainment "
    "zones, and advanced building management systems.\n\n"
    "Its proximity to major landmarks like DND Flyway, Sector 18, and "
    "upcoming infrastructure developments further enhances its value, "
    "making it a promising commercial destination in Noida."
)


CRC_STATS = [
    ("Property Status",     "Under Construction",  "status",    1),
    ("Property Type",       "Retail/Office Space", "type",      2),
    ("Price Starts from",   "80 Lacs*",            "price",     3),
    ("Sizes",               "360 Sq.Ft. onwards",  "size",      4),
    ("Developer",           "CRC GROUP",           "developer", 5),
]


CRC_HIGHLIGHTS = [
    "Prime Corner Plot in Sec 140A, Noida",
    "Team of Experts like BENOY LONDON / RSP SINGAPORE",
    "Payment Plan 33:33:33",
    "IGBC-Platinum Certified Building",
    "Superior Infrastructure coupled with urban planning",
    "20% green area across the land",
    "Privatized power distribution for reliable supply",
    "Projected monthly rental ~₹80K",
]


class Command(BaseCommand):
    help = "Seed demo projects from the frontend bundle, including placeholder media."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-media", action="store_true",
            help="Skip placeholder image / floor-plan generation.",
        )

    def handle(self, *args, **opts):
        now = timezone.now()
        skip_media = opts.get("skip_media", False)
        for title, cat_name, city_name, locality, tagline, featured, order, dev_name in PROJECTS:
            try:
                category = Category.objects.get(name=cat_name)
                city = City.objects.get(name=city_name)
            except (Category.DoesNotExist, City.DoesNotExist):
                self.stderr.write(self.style.ERROR(
                    f"Run `manage.py seed_catalog` first — missing "
                    f"category '{cat_name}' or city '{city_name}'."
                ))
                return

            developer = Developer.objects.filter(name=dev_name).first()

            project, _ = Project.objects.update_or_create(
                title=title,
                defaults={
                    "category": category,
                    "city": city,
                    "locality": locality,
                    "developer": developer,
                    "tagline": tagline,
                    "is_featured": featured,
                    "featured_order": order,
                    "is_published": True,
                    "published_at": now,
                    "status": Project.Status.UNDER_CONSTRUCTION,
                },
            )

            if title == "CRC The Flagship":
                project.description = CRC_DESCRIPTION
                project.price_starting_lacs = 80
                project.price_display = "80 Lacs*"
                project.size_display = "360 Sq.Ft. onwards"
                project.property_type = "Retail/Office Space"
                project.rera_number = "UPRERAPRJ123456"
                project.save()

                project.amenities.set(Amenity.objects.all())

                project.stats.all().delete()
                for label, value, icon_key, order_ in CRC_STATS:
                    ProjectStat.objects.create(
                        project=project, label=label, value=value,
                        icon_key=icon_key, display_order=order_,
                    )

                project.highlights.all().delete()
                for i, text in enumerate(CRC_HIGHLIGHTS, start=1):
                    ProjectHighlight.objects.create(
                        project=project, text=text, display_order=i,
                    )

            # ---- Placeholder media ---------------------------------------
            if skip_media:
                continue

            # Cover image
            if not project.cover_image:
                project.cover_image.save(
                    "cover.jpg",
                    ContentFile(_generate_placeholder(project.title, "Cover")),
                    save=True,
                )

            # Gallery: 4 images, first one primary
            if project.images.count() == 0:
                for i in range(1, 5):
                    ProjectImage.objects.create(
                        project=project,
                        image=ContentFile(
                            _generate_placeholder(project.title, f"Gallery #{i}"),
                            name=f"gallery-{i}.jpg",
                        ),
                        display_order=i,
                        is_primary=(i == 1),
                        alt_text=f"{project.title} — view {i}",
                    )

            # One floor plan per project
            if project.floor_plans.count() == 0:
                FloorPlan.objects.create(
                    project=project,
                    file=ContentFile(
                        _generate_floor_plan(project.title),
                        name="floor-plan-typical.jpg",
                    ),
                    label="Typical Floor",
                    alt_text=f"{project.title} floor plan",
                    display_order=1,
                )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {Project.objects.count()} projects "
            f"({Project.objects.filter(is_featured=True).count()} featured)."
        ))
