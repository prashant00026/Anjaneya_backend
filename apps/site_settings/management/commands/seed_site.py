"""Seed singleton SiteSettings, the 4 CMS pages, the 3 testimonials,
and the 4 team members from the live frontend bundle."""

from django.core.management.base import BaseCommand

from site_settings.models import CmsPage, SiteSettings
from team.models import TeamMember
from testimonials.models import Testimonial


TEAM = [
    ("Rohit Aggarwal", "Founder & CEO",
     "Rohit Aggarwal brings over 15 years of experience in real estate "
     "sales, marketing, and investment advisory. Before founding "
     "Anjaneya Global Realty, he spent nearly 11 years as Assistant "
     "Director — Sales & Marketing at Bullmen Realty India.",
     "https://www.linkedin.com/in/rohit-aggarwal-1b900035/"),
    ("Vikrant Singh", "Co-Founder & COO",
     "Vikrant Singh brings over 13 years of experience in luxury real "
     "estate sales and marketing across both residential and commercial "
     "segments. As COO, he oversees day-to-day operations.",
     "https://www.linkedin.com/in/vikrant-singh-57035324/"),
    ("Raunak Verma", "Co-Founder & CMO",
     "Raunak Verma is a seasoned real estate sales and marketing "
     "professional with over 10 years of progressive experience in "
     "luxury and high-value residential and commercial deals.",
     "https://www.linkedin.com/in/raunak-verma-7698151b0/"),
    ("Upender Singh", "Director — Investment Strategy",
     "Upender Singh is a seasoned real estate leader and investment "
     "strategist with over 8 years of experience across India's luxury "
     "and commercial real estate landscape.",
     ""),
]

TESTIMONIALS = [
    ("Rajiv Kapoor", "Business Owner",
     "Anjaneya Global Realty helped me secure a premium office space "
     "in Noida within my budget. Their market intelligence and "
     "personalized approach was exceptional. Truly a cut above the rest."),
    ("Priya Sharma", "IT Professional",
     "As a first-time homebuyer, I was overwhelmed by the options in "
     "Gurugram. The team at Anjaneya provided clear, honest advice and "
     "guided me through every step of the process. Highly recommended!"),
    ("Vikram Malhotra", "Retail Entrepreneur",
     "Their expertise in commercial real estate is unmatched. They "
     "understood our requirement for a retail flagship store and found "
     "the perfect high-visibility location. Professionalism at its best."),
]

CMS_PAGES = [
    ("about", "About Anjaneya Global Realty",
     "Anjaneya Global Realty is Delhi NCR's premier real estate "
     "consultancy. We empower investors and homebuyers to make "
     "confident, strategic property decisions across the Delhi NCR region."),
    ("privacy", "Privacy Policy",
     "Placeholder privacy policy — replace via /admin/site_settings/cmspage/."),
    ("terms", "Terms of Service",
     "Placeholder terms of service — replace via /admin/site_settings/cmspage/."),
    ("disclaimer", "Disclaimer",
     "Placeholder disclaimer — replace via /admin/site_settings/cmspage/."),
]


class Command(BaseCommand):
    help = "Seed SiteSettings, CmsPages, TeamMembers, Testimonials."

    def handle(self, *args, **opts):
        s = SiteSettings.load()
        s.phone = "+91 73111 03111"
        s.email = "info@anjaneyaglobalrealty.com"
        s.address = (
            "Office No. 106, 1st Floor, Tower 4, Assotech Business "
            "Cresterra, Sector 135, Noida Expressway, Noida – 201304"
        )
        s.whatsapp_url = "https://wa.me/917311103111"
        s.instagram_url = "https://www.instagram.com/anjaneya.global.realty/"
        s.linkedin_url = "https://www.linkedin.com/company/anjaneya-global-realty/"
        s.facebook_url = "https://www.facebook.com/profile.php?id=61576461473513"
        s.youtube_url = "https://www.youtube.com/@RohitfromAnjaneyaGlobalRealty"
        s.hero_stat_clients = "98+"
        s.hero_stat_clients_label = "Happy clients, countless smiles delivered"
        s.hero_stat_value = "100Cr+"
        s.hero_stat_value_label = "Property value managed with excellence"
        s.copyright_year = 2026
        s.save()

        for i, (name, role, content) in enumerate(TESTIMONIALS, start=1):
            Testimonial.objects.update_or_create(
                name=name,
                defaults={"role": role, "content": content, "display_order": i},
            )

        for i, (name, designation, bio, linkedin) in enumerate(TEAM, start=1):
            TeamMember.objects.update_or_create(
                name=name,
                defaults={
                    "designation": designation,
                    "bio": bio,
                    "linkedin_url": linkedin,
                    "display_order": i,
                },
            )

        for slug, title, body in CMS_PAGES:
            CmsPage.objects.update_or_create(
                slug=slug,
                defaults={"title": title, "body": body, "is_published": True},
            )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded SiteSettings, "
            f"{Testimonial.objects.count()} testimonials, "
            f"{TeamMember.objects.count()} team members, "
            f"{CmsPage.objects.count()} CMS pages."
        ))
