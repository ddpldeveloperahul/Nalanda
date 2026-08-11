from django.core.management.base import BaseCommand
from django.utils import timezone
from myapp.models import Department, District, Report, ReportCategory


class Command(BaseCommand):
    help = "Seeds initial Report Generation & Export Center data matching UI screenshots."

    def handle(self, *args, **options):
        dept = Department.objects.filter(name__icontains="Water").first() or Department.objects.first()
        dist = District.objects.filter(name="Nalanda").first() or District.objects.first()

        dept_name = dept.name if dept else "Water & Sanitation (JJM)"

        reports_data = [
            {
                "code": "REP-001",
                "title": f"{dept_name} Monthly Sector SLA Audit",
                "category": ReportCategory.SLA_AUDIT,
                "file_size_str": "2.4 MB",
                "download_format": "PDF",
                "department": dept,
                "district": dist,
            },
            {
                "code": "REP-002",
                "title": f"{dept_name} Asset Geotag Verification Log",
                "category": ReportCategory.ASSET_AUDIT,
                "file_size_str": "4.1 MB",
                "download_format": "CSV",
                "department": dept,
                "district": dist,
            },
            {
                "code": "REP-003",
                "title": f"{dept_name} Citizen Grievances & Resolution Summary",
                "category": ReportCategory.GRIEVANCE_LOG,
                "file_size_str": "1.8 MB",
                "download_format": "PDF",
                "department": dept,
                "district": dist,
            },
        ]

        created_count = 0
        for item in reports_data:
            report, created = Report.objects.get_or_create(
                code=item["code"],
                defaults=item
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully seeded {created_count} reports. Total in DB: {Report.objects.count()}.")
        )
