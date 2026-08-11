from django.core.management.base import BaseCommand
from myapp.models import Department, District, ProjectExecution, SiteDiary, MeasurementBook, ProjectBill, ExecutionRisk, ProjectStatus, RiskSeverity

class Command(BaseCommand):
    help = "Seeds initial sample data for Government Project Execution ERP."

    def handle(self, *args, **options):
        dept = Department.objects.filter(name__icontains="Water").first() or Department.objects.first()
        dist = District.objects.filter(name__icontains="Nalanda").first() or District.objects.first()

        proj, created = ProjectExecution.objects.get_or_create(
            project_id="PRJ-2026-00103",
            defaults={
                "title": "Surajpur Ward 3 Elevated Water Reservoir",
                "department": dept,
                "district": dist,
                "block": "Surajpur",
                "ward": "Ward 3",
                "contractor_name": "Bihar Jal Nigam Infra Pvt Ltd",
                "sanction_amount": 12000000.00,
                "expenditure_amount": 11400000.00,
                "progress_percentage": 100.00,
                "status": ProjectStatus.COMPLETED,
                "risk_level": RiskSeverity.HIGH,
                "inspection_due": True,
            }
        )

        if not created:
            proj.title = "Surajpur Ward 3 Elevated Water Reservoir"
            proj.department = dept
            proj.district = dist
            proj.sanction_amount = 12000000.00
            proj.expenditure_amount = 11400000.00
            proj.progress_percentage = 100.00
            proj.status = ProjectStatus.COMPLETED
            proj.risk_level = RiskSeverity.HIGH
            proj.inspection_due = True
            proj.save()

        # Seed Risk Signal
        ExecutionRisk.objects.get_or_create(
            project=proj,
            risk_signal="Intermittent monsoon waterlogging delayed concrete drying by 8 days.",
            defaults={
                "severity": RiskSeverity.HIGH,
                "recommendation": "Inspect site / control release",
                "status": "active"
            }
        )

        # Seed Site Diary
        SiteDiary.objects.get_or_create(
            project=proj,
            work_description="Final concrete curing and hydrostatic testing of elevated water tank.",
            defaults={
                "labour_count": 18,
                "materials_used": "Cement Grade M25, Reinforcement Steel 12mm",
                "weather_condition": "Sunny",
                "progress_logged": 100.00
            }
        )

        # Seed MB Entry
        MeasurementBook.objects.get_or_create(
            mb_number="MB-2026-00103",
            project=proj,
            defaults={
                "item_description": "Construction of 500KL RCC Overhead Tank at Surajpur",
                "unit": "Job",
                "quantity_measured": 1.000,
                "rate": 12000000.00,
                "total_amount": 12000000.00,
                "measured_by": "Eng. Vijay Kumar (JE)",
                "verified_by": "R.K. Singh (EE)",
                "status": "verified"
            }
        )

        # Seed Bill
        ProjectBill.objects.get_or_create(
            bill_number="RA-BILL-2026-00103",
            project=proj,
            defaults={
                "bill_type": "FINAL_BILL",
                "claimed_amount": 12000000.00,
                "verified_amount": 11400000.00,
                "deductions": 600000.00,
                "net_payable_amount": 11400000.00,
                "payment_status": "approved",
                "transaction_reference": "PFMS-NLND-2026-98123"
            }
        )

        self.stdout.write(self.style.SUCCESS("Successfully seeded Project Execution ERP data!"))
