from django.core.management.base import BaseCommand
from myapp.services.complaint_service import seed_default_complaint_categories


class Command(BaseCommand):
    help = "Seeds default complaint categories, auto-routing department mappings, and SLA targets."

    def handle(self, *args, **options):
        self.stdout.write("Seeding complaint categories and auto-routing targets...")
        seed_default_complaint_categories()
        self.stdout.write(self.style.SUCCESS("Successfully seeded default complaint categories!"))
