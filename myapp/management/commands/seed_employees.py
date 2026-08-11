from django.core.management.base import BaseCommand
from myapp.models import Department, District, Employee, EmployeeStatus, Role, RoleName, User


class Command(BaseCommand):
    help = "Seeds initial Employee Directory data matching UI screenshots."

    def handle(self, *args, **options):
        dept = Department.objects.filter(name__icontains="Water").first() or Department.objects.first()
        dist = District.objects.filter(name="Nalanda").first() or District.objects.first()
        role_head = Role.objects.filter(code=RoleName.DEPARTMENT_HEAD).first() or Role.objects.first()
        role_officer = Role.objects.filter(code=RoleName.DEPARTMENT_OFFICER).first() or Role.objects.first()

        employees_data = [
            {
                "employee_code": "GOV-100101",
                "full_name": "Eng. Vijay Kumar",
                "email": "vijay.kumar@nalanda.gov.in",
                "designation": "Executive Engineer",
                "office": "District Water Office",
                "block": "Silao",
                "role_obj": role_head,
                "status": EmployeeStatus.ACTIVE,
                "department": dept,
                "district": dist,
            },
            {
                "employee_code": "GOV-100102",
                "full_name": "Anil Mehta",
                "email": "anil.mehta@nalanda.gov.in",
                "designation": "Assistant Engineer",
                "office": "District Water Office",
                "block": "Silao",
                "role_obj": role_officer,
                "status": EmployeeStatus.ACTIVE,
                "department": dept,
                "district": dist,
            },
        ]

        created_count = 0
        head_emp = None

        for item in employees_data:
            r_obj = item.pop("role_obj")
            user_obj, _ = User.objects.get_or_create(
                username=item["email"],
                defaults={
                    "email": item["email"],
                    "first_name": item["full_name"].split()[0],
                    "last_name": " ".join(item["full_name"].split()[1:]) if " " in item["full_name"] else "",
                    "role": r_obj,
                    "department": dept,
                    "district": dist,
                }
            )
            if user_obj and not user_obj.role:
                user_obj.role = r_obj
                user_obj.save()

            emp, created = Employee.objects.get_or_create(
                employee_code=item["employee_code"],
                defaults={
                    **item,
                    "user": user_obj,
                    "reports_to": head_emp if head_emp else None
                }
            )
            if not head_emp:
                head_emp = emp

            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully seeded {created_count} employees. Total in DB: {Employee.objects.count()}.")
        )
