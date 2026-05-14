"""Idempotently seed cities, categories, developers, amenities.

Data is drawn from the frontend audit:
  - cities seen on Projects-list: Noida, Greater Noida, Gurugram,
    Faridabad, Ghaziabad
  - categories from the home-page section labels
  - developers inferred from project titles / "About Developer" block
  - amenity set from the CRC The Flagship detail page
"""

from django.core.management.base import BaseCommand

from catalog.models import Amenity, Category, City, Developer


CITIES = [
    ("Noida", 1),
    ("Greater Noida", 2),
    ("Gurugram", 3),
    ("Faridabad", 4),
    ("Ghaziabad", 5),
]

CATEGORIES = [
    ("Residential", 1,
     "From affordable homes to ultra-luxury apartments across Noida, "
     "Greater Noida and Gurgaon."),
    ("Commercial", 2,
     "Premium office spaces, retail hubs, and business parks across the "
     "Delhi NCR commercial corridors."),
    ("Luxury", 3,
     "Exclusive properties for discerning buyers — curated luxury real "
     "estate with unmatched amenities."),
]

DEVELOPERS = [
    "CRC Group",
    "Godrej Properties",
    "Ace Group",
    "Group 108",
    "Eldeco",
    "Harmony Builders",
    "Sunrise Developers",
]

AMENITIES = [
    "Hi-Tech Security",
    "Ample Parking",
    "24/7 Power Backup",
    "High-speed Internet",
    "Hi-speed Elevators",
    "Business Lounges",
    "Biometric Entry",
    "ATMs & Bank Facilities",
    "EV Charging Stations",
    "Pharmacy & Health Care",
]


class Command(BaseCommand):
    help = "Seed reference data (cities, categories, developers, amenities)."

    def handle(self, *args, **opts):
        for name, order in CITIES:
            City.objects.update_or_create(
                name=name, defaults={"display_order": order},
            )
        for name, order, desc in CATEGORIES:
            Category.objects.update_or_create(
                name=name,
                defaults={"display_order": order, "description": desc},
            )
        for name in DEVELOPERS:
            Developer.objects.get_or_create(name=name)
        for i, name in enumerate(AMENITIES, start=1):
            Amenity.objects.update_or_create(
                name=name, defaults={"display_order": i},
            )
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {City.objects.count()} cities, "
            f"{Category.objects.count()} categories, "
            f"{Developer.objects.count()} developers, "
            f"{Amenity.objects.count()} amenities."
        ))
