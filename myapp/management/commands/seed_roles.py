from django.core.management.base import BaseCommand
from myapp.models import Role, RoleName, ScopeLevel


class Command(BaseCommand):
    help = "Seeds official NDISP RBAC roles including State Administration roles"

    def handle(self, *args, **options):
        roles_data = [
            {
                "name": "State Super Admin",
                "code": RoleName.STATE_SUPER_ADMIN,
                "scope_level": ScopeLevel.STATE,
                "description": "State Super Admin with full system level administration and governance",
            },
            {
                "name": "State Admin",
                "code": RoleName.STATE_ADMIN,
                "scope_level": ScopeLevel.STATE,
                "description": "Full administrative control across all districts in assigned state",
            },
            {
                "name": "State Finance Admin",
                "code": RoleName.STATE_FINANCE_ADMIN,
                "scope_level": ScopeLevel.STATE,
                "description": "State Finance Administrator for scheme budget mapping, fund releases & financial ledger",
            },
            {
                "name": "State Department Admin",
                "code": RoleName.STATE_DEPARTMENT_ADMIN,
                "scope_level": ScopeLevel.STATE,
                "description": "State Department Administrator for sector-wide line department oversight",
            },
            {
                "name": "State Monitoring Officer",
                "code": RoleName.STATE_MONITORING_OFFICER,
                "scope_level": ScopeLevel.STATE,
                "description": "State Monitoring & Evaluation Officer for audit tracking and KPI metrics",
            },
            {
                "name": "State GIS Admin",
                "code": RoleName.STATE_GIS_ADMIN,
                "scope_level": ScopeLevel.STATE,
                "description": "State GIS & Asset Management Administrator for geospatial layer cataloging",
            },
            {
                "name": "System Administrator",
                "code": RoleName.SYSTEM_ADMINISTRATOR,
                "scope_level": ScopeLevel.STATE,
                "description": "System Administrator for user directory, workflow authority & security settings",
            },
            {
                "name": "District Collector",
                "code": RoleName.DISTRICT_COLLECTOR,
                "scope_level": ScopeLevel.DISTRICT,
                "description": "Full control within assigned district across all departments",
            },
            {
                "name": "District Magistrate (DM)",
                "code": RoleName.DISTRICT_MAGISTRATE,
                "scope_level": ScopeLevel.DISTRICT,
                "description": "Executive oversight, financial sanction & override authority",
            },
            {
                "name": "Additional District Magistrate (ADM)",
                "code": RoleName.ADM,
                "scope_level": ScopeLevel.DISTRICT,
                "description": "Delegated control within assigned district and assigned departments",
            },
            {
                "name": "Department Head",
                "code": RoleName.DEPARTMENT_HEAD,
                "scope_level": ScopeLevel.DEPARTMENT,
                "description": "Line department queue management, officer tasking, employee onboarding",
            },
            {
                "name": "Department Officer",
                "code": RoleName.DEPARTMENT_OFFICER,
                "scope_level": ScopeLevel.DEPARTMENT,
                "description": "Manage assigned complaints queue, schedule inspections, resolve tickets",
            },
            {
                "name": "Executive / Assistant Engineer",
                "code": RoleName.EXECUTIVE_ENGINEER,
                "scope_level": ScopeLevel.DEPARTMENT,
                "description": "Job execution, site progress, e-MB verification & bill submission",
            },
            {
                "name": "Field Inspector / Junior Engineer",
                "code": RoleName.FIELD_INSPECTOR,
                "scope_level": ScopeLevel.DEPARTMENT,
                "description": "Site geotag verification & evidence upload",
            },
            {
                "name": "Field Supervisor",
                "code": RoleName.FIELD_SUPERVISOR,
                "scope_level": ScopeLevel.DEPARTMENT,
                "description": "Field operations supervision & inspection report verification",
            },
            {
                "name": "Citizen",
                "code": RoleName.CITIZEN,
                "scope_level": ScopeLevel.SELF,
                "description": "Public user managing own grievances and viewing public maps",
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
