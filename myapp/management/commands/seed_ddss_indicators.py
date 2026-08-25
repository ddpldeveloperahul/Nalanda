from django.core.management.base import BaseCommand
from myapp.models import (
    Department, District, Block, Facility, DepartmentIndicator,
    EducationFacilityIndicator, WaterFacilityIndicator, RoadIndicator, PriorityLocation
)

class Command(BaseCommand):
    help = "Seed DDSS multi-department indicators for Health, Education, Water Resources, and PWD."

    def handle(self, *args, **options):
        self.stdout.write("Seeding DDSS multi-department indicators...")

        district = District.objects.filter(name="Nalanda").first() or District.objects.first()
        if not district:
            self.stdout.write(self.style.ERROR("No District found. Seed state/district first."))
            return

        silao_block = Block.objects.filter(subdivision__district=district, name__icontains="Silao").first() or Block.objects.first()

        # 1. Health Indicators
        dept_health, _ = Department.objects.get_or_create(code="HEALTH", defaults={"name": "Health & Family Welfare"})
        fac_health, _ = Facility.objects.get_or_create(
            name="Silao Primary Health Centre",
            defaults={"department": dept_health, "district": district}
        )
        DepartmentIndicator.objects.update_or_create(
            department=dept_health, district=district, block=silao_block, facility=fac_health, indicator_code="DOCTOR_VACANCY",
            defaults={
                "indicator_name": "Doctor Vacancies Count",
                "value": 4.0, "unit": "posts", "period": "2026-08", "source": "District Health Society",
                "data_status": "VERIFIED"
            }
        )

        # 2. Education Indicators
        dept_edu, _ = Department.objects.get_or_create(code="EDUCATION", defaults={"name": "Education Department"})
        fac_edu, _ = Facility.objects.get_or_create(
            name="Government High School Silao",
            defaults={"department": dept_edu, "district": district}
        )
        EducationFacilityIndicator.objects.update_or_create(
            facility=fac_edu, period="2026-08",
            defaults={
                "sanctioned_teachers": 15, "available_teachers": 9, "student_enrolment": 450,
                "classroom_count": 10, "drinking_water_status": True, "separate_girls_toilet": False
            }
        )
        DepartmentIndicator.objects.update_or_create(
            department=dept_edu, district=district, block=silao_block, facility=fac_edu, indicator_code="TEACHER_VACANCY",
            defaults={
                "indicator_name": "Primary School Teacher Vacancies",
                "value": 6.0, "unit": "posts", "period": "2026-08", "source": "Education MIS",
                "data_status": "VERIFIED"
            }
        )

        # 3. Water Resources Indicators
        dept_wtr, _ = Department.objects.get_or_create(code="WATER_RESOURCES", defaults={"name": "Water Resources Department"})
        WaterFacilityIndicator.objects.update_or_create(
            facility=fac_health, period="2026-08",
            defaults={
                "household_coverage_percent": 62.5, "functional_tap_connections": 320,
                "non_functional_sources_count": 3, "daily_supply_hours": 3.5, "water_quality_status": "SAFE"
            }
        )
        DepartmentIndicator.objects.update_or_create(
            department=dept_wtr, district=district, block=silao_block, indicator_code="WATER_COVERAGE",
            defaults={
                "indicator_name": "Household Tap Water Coverage",
                "value": 62.5, "unit": "percent", "period": "2026-08", "source": "Jal Jeevan Mission",
                "data_status": "VERIFIED"
            }
        )

        # 4. PWD Road Indicators
        dept_pwd, _ = Department.objects.get_or_create(code="PWD", defaults={"name": "Public Works Department (PWD)"})
        RoadIndicator.objects.update_or_create(
            road_name="Silao-Rajgir Rural Link Road", block=silao_block,
            defaults={
                "department": dept_pwd, "district": district, "road_length_km": 18.5,
                "paved_length_km": 11.0, "unpaved_poor_length_km": 7.5, "accessibility_status": "POOR",
                "bridge_gap_count": 2
            }
        )
        DepartmentIndicator.objects.update_or_create(
            department=dept_pwd, district=district, block=silao_block, indicator_code="POOR_ROAD_LENGTH",
            defaults={
                "indicator_name": "Unpaved Poor Monsoon Connectivity Length",
                "value": 7.5, "unit": "km", "period": "2026-08", "source": "PWD Infrastructure Survey",
                "data_status": "VERIFIED"
            }
        )

        # 5. Create Priority Locations for Education, Water & PWD
        PriorityLocation.objects.get_or_create(
            title="Silao High School Girls Toilet & Teacher Deficit",
            department=dept_edu, district=district, block=silao_block, facility=fac_edu,
            defaults={"gap_score": 78.5, "priority": "P1", "recommended_action": "Sanction 6 Teacher Posts & Construct Separate Girls Sanitation Block"}
        )

        PriorityLocation.objects.get_or_create(
            title="Silao Block Water Coverage Deficit",
            department=dept_wtr, district=district, block=silao_block,
            defaults={"gap_score": 72.0, "priority": "P2", "recommended_action": "Extend Jal Jeevan Mission Solar Tap Water Scheme"}
        )

        PriorityLocation.objects.get_or_create(
            title="Silao-Rajgir Unpaved Monsoon Connectivity Void",
            department=dept_pwd, district=district, block=silao_block,
            defaults={"gap_score": 84.0, "priority": "P1", "recommended_action": "Pave 7.5 km All-Weather Road & Construct 2 Culvert Bridges"}
        )

        self.stdout.write(self.style.SUCCESS("Successfully seeded DDSS multi-department indicators!"))
