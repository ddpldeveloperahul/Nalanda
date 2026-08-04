from django.core.management.base import BaseCommand
from myapp.models import Role, RoleName, ScopeLevel


class Command(BaseCommand):
    help = "Seeds official NDISP RBAC roles per Blueprint Section 9.1 specification"

    def handle(self, *args, **options):
        roles_data = [
            {
                "name": "National Admin",
                "code": RoleName.NATIONAL_ADMIN,
                "scope_level": ScopeLevel.NATIONAL,
                "description": "Full system control across all states and districts",
            },
            {
                "name": "State Admin",
                "code": RoleName.STATE_ADMIN,
                "scope_level": ScopeLevel.STATE,
                "description": "Full administrative control across all districts in assigned state",
            },
            {
                "name": "District Collector / DM",
                "code": RoleName.DISTRICT_COLLECTOR,
                "scope_level": ScopeLevel.DISTRICT,
                "description": "Full control within assigned district across all departments",
            },
            {
                "name": "Additional District Magistrate (ADM)",
                "code": RoleName.ADM,
                "scope_level": ScopeLevel.DISTRICT,
                "description": "Delegated control within assigned district and assigned departments",
            },
            {
                "name": "Department Officer",
                "code": RoleName.DEPARTMENT_OFFICER,
                "scope_level": ScopeLevel.DEPARTMENT,
                "description": "Full control within assigned district and department",
            },
            {
                "name": "Field Engineer / Data Entry Operator",
                "code": RoleName.FIELD_ENGINEER_DEO,
                "scope_level": ScopeLevel.DEPARTMENT,
                "description": "Asset CRUD & inspection updates within assigned district and department",
            },
            {
                "name": "Registered Citizen",
                "code": RoleName.CITIZEN_REGISTERED,
                "scope_level": ScopeLevel.SELF,
                "description": "Public user managing own grievances and viewing public maps",
            },
            {
                "name": "Anonymous Citizen",
                "code": RoleName.CITIZEN_ANONYMOUS,
                "scope_level": ScopeLevel.ANONYMOUS,
                "description": "Public read-only user",
            },
        ]

        created_count = 0
        for item in roles_data:
            role, created = Role.objects.get_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "scope_level": item["scope_level"],
                    "description": item["description"],
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created role: {role.name} ({role.scope_level})"))
            else:
                role.name = item["name"]
                role.scope_level = item["scope_level"]
                role.description = item["description"]
                role.save()
                self.stdout.write(f"Updated role: {role.name}")

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(roles_data)} NDISP Roles."))
