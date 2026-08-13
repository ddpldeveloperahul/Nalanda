from django.core.management.base import BaseCommand
from myapp.models import (
    State,
    District,
    Department,
    StateBudget,
    DepartmentBudget,
    DistrictAllocation,
    SchemeMaster,
    FinancialLedgerEntry,
)


class Command(BaseCommand):
    help = "Seeds State Governance Master Budget, Department Budgets, District Allocations, Schemes & Financial Ledger."

    def handle(self, *args, **options):
        # 1. Ensure State object
        state_obj, _ = State.objects.get_or_create(
            name="Bihar",
            defaults={"code": "BR", "census_code": 10}
        )

        # 2. Seed 8 Departments
        departments_data = [
            "Health & Family Welfare",
            "School Education",
            "Public Works Department",
            "Electricity Board",
            "Urban Local Body / Sanitation",
            "Solar & Renewable Energy",
            "Tourism & Heritage Development",
            "Water & Sanitation (Jal Jeevan Mission)",
        ]

        dept_objs = {}
        for dept_name in departments_data:
            d_obj, _ = Department.objects.get_or_create(name=dept_name)
            dept_objs[dept_name] = d_obj

        # 3. Seed 10 Districts
        districts_data = [
            "Nalanda",
            "Patna",
            "Gaya",
            "Muzaffarpur",
            "Bhagalpur",
            "Darbhanga",
            "Begusarai",
            "Sitamarhi",
            "Madhubani",
            "Vaishali",
        ]

        dist_objs = {}
        for dist_name in districts_data:
            dist_obj, _ = District.objects.get_or_create(
                name=dist_name,
                defaults={"state": state_obj, "lgd_code": 100 + len(dist_objs)}
            )
            dist_objs[dist_name] = dist_obj

        # 4. Create State Master Budget for FY 2026-27
        sb_obj, _ = StateBudget.objects.get_or_create(
            financial_year="2026-27",
            defaults={
                "total_state_budget_cr": 4800.00,
                "department_allocation_cr": 4600.00,
                "district_allocation_cr": 899.00,
                "total_sanctioned_cr": 4.00,
                "total_released_cr": 3900.00,
                "total_committed_cr": 3200.00,
                "total_utilized_cr": 2850.00,
                "available_balance_cr": 4596.00,
                "unreleased_balance_cr": 4.00,
                "active_projects_count": 10,
                "at_risk_projects_count": 4,
                "pending_approvals_count": 4,
            }
        )
        if not _:
            sb_obj.total_state_budget_cr = 4800.00
            sb_obj.department_allocation_cr = 4600.00
            sb_obj.district_allocation_cr = 899.00
            sb_obj.total_sanctioned_cr = 4.00
            sb_obj.total_released_cr = 3900.00
            sb_obj.total_committed_cr = 3200.00
            sb_obj.total_utilized_cr = 2850.00
            sb_obj.available_balance_cr = 4596.00
            sb_obj.unreleased_balance_cr = 4.00
            sb_obj.active_projects_count = 10
            sb_obj.at_risk_projects_count = 4
            sb_obj.pending_approvals_count = 4
            sb_obj.save()

        # 5. Seed Department Budgets
        dept_budgets = [
            ("School Education", 1000.00, 980.00, 900.00, 850.00, 750.00),
            ("Health & Family Welfare", 950.00, 890.00, 800.00, 720.00, 680.00),
            ("Public Works Department", 750.00, 700.00, 650.00, 580.00, 510.00),
            ("Electricity Board", 600.00, 580.00, 500.00, 420.00, 390.00),
            ("Urban Local Body / Sanitation", 500.00, 460.00, 400.00, 310.00, 260.00),
            ("Water & Sanitation (Jal Jeevan Mission)", 450.00, 420.00, 380.00, 210.00, 180.00),
            ("Solar & Renewable Energy", 200.00, 180.00, 150.00, 80.00, 50.00),
            ("Tourism & Heritage Development", 150.00, 120.00, 120.00, 30.00, 30.00),
        ]

        for name, auth, sanc, rel, comm, util in dept_budgets:
            dept_obj = dept_objs.get(name)
            if dept_obj:
                db, _ = DepartmentBudget.objects.get_or_create(
                    department=dept_obj,
                    financial_year="2026-27",
                    defaults={
                        "authorized_budget_cr": auth,
                        "sanctioned_budget_cr": sanc,
                        "released_budget_cr": rel,
                        "committed_budget_cr": comm,
                        "utilized_budget_cr": util,
                    }
                )
                if not _:
                    db.authorized_budget_cr = auth
                    db.sanctioned_budget_cr = sanc
                    db.released_budget_cr = rel
                    db.committed_budget_cr = comm
                    db.utilized_budget_cr = util
                    db.save()

        # 6. Seed District Allocations for ALL Districts in Database
        preset_allocations = {
            "Patna": (240.00, 200.00, 180.00),
            "Nalanda": (150.00, 130.00, 110.00),
            "Gaya": (135.00, 115.00, 95.00),
            "Muzaffarpur": (110.00, 90.00, 80.00),
            "Bhagalpur": (95.00, 80.00, 70.00),
            "Darbhanga": (65.00, 50.00, 45.00),
            "Begusarai": (45.00, 35.00, 30.00),
            "Sitamarhi": (35.00, 25.00, 20.00),
            "Madhubani": (14.00, 10.00, 8.00),
            "Vaishali": (10.00, 8.00, 6.00),
        }

        all_districts = District.objects.all()
        for idx, dist_obj in enumerate(all_districts):
            d_name = dist_obj.name
            if d_name in preset_allocations:
                alloc, sanc, util = preset_allocations[d_name]
            else:
                # Dynamic default allocation for remaining districts
                alloc = round(25.00 + (idx % 15) * 2.5, 2)
                sanc = round(alloc * 0.85, 2)
                util = round(sanc * 0.75, 2)

            da, _ = DistrictAllocation.objects.get_or_create(
                district=dist_obj,
                financial_year="2026-27",
                defaults={
                    "allocation_amount_cr": alloc,
                    "sanctioned_amount_cr": sanc,
                    "utilized_amount_cr": util,
                }
            )
            if not _:
                da.allocation_amount_cr = alloc
                da.sanctioned_amount_cr = sanc
                da.utilized_amount_cr = util
                da.save()

        # 7. Seed Schemes
        schemes_data = [
            ("SCH-HEALTH-001", "Ayushman Bharat (PM-JAY) State Continuation", "Health & Family Welfare", 300.00, 280.00, 250.00, 210.00),
            ("SCH-HEALTH-002", "National Health Mission (State Share)", "Health & Family Welfare", 450.00, 420.00, 380.00, 330.00),
            ("SCH-HEALTH-003", "Mukhyamantri Arogya Scheme", "Health & Family Welfare", 200.00, 190.00, 170.00, 140.00),
            ("SCH-EDU-001", "Samagra Shiksha Abhiyan", "School Education", 600.00, 590.00, 550.00, 480.00),
            ("SCH-EDU-002", "Bihar Vikas Mission (Education)", "School Education", 400.00, 390.00, 350.00, 270.00),
            ("SCH-PWD-001", "PMGSY Road Connectivity", "Public Works Department", 450.00, 420.00, 400.00, 320.00),
            ("SCH-PWD-002", "State Highways Development Programme", "Public Works Department", 300.00, 280.00, 250.00, 190.00),
            ("SCH-ELEC-001", "Rural Feeder Strengthening Scheme", "Electricity Board", 350.00, 340.00, 300.00, 240.00),
            ("SCH-ELEC-002", "PM Surya Ghar Muft Bijli Yojana", "Electricity Board", 250.00, 240.00, 200.00, 150.00),
            ("SCH-URBAN-001", "Swachh Bharat Mission 2.0 (Urban)", "Urban Local Body / Sanitation", 300.00, 280.00, 240.00, 160.00),
            ("SCH-URBAN-002", "AMRUT 2.0 (Urban Infrastructure)", "Urban Local Body / Sanitation", 200.00, 180.00, 160.00, 100.00),
            ("SCH-SOLAR-001", "Bihar Rooftop Solar Programme", "Solar & Renewable Energy", 200.00, 180.00, 150.00, 50.00),
            ("SCH-TOUR-001", "Swadesh Darshan (Circuit Development)", "Tourism & Heritage Development", 150.00, 120.00, 120.00, 30.00),
            ("SCH-WATER-001", "Jal Jeevan Mission (Functionality)", "Water & Sanitation (Jal Jeevan Mission)", 450.00, 420.00, 380.00, 180.00),
        ]

        for code, sname, dname, alloc, sanc, rel, util in schemes_data:
            dept_obj = dept_objs.get(dname)
            if dept_obj:
                sch, _ = SchemeMaster.objects.get_or_create(
                    code=code,
                    defaults={
                        "name": sname,
                        "department": dept_obj,
                        "total_allocation_cr": alloc,
                        "sanctioned_cr": sanc,
                        "released_cr": rel,
                        "utilized_cr": util,
                    }
                )
                if not _:
                    sch.name = sname
                    sch.department = dept_obj
                    sch.total_allocation_cr = alloc
                    sch.sanctioned_cr = sanc
                    sch.released_cr = rel
                    sch.utilized_cr = util
                    sch.save()

        # 8. Seed Financial Ledger Entries
        ledger_entries = [
            ("TXN-FIN-2026-001", "PROVISION", None, None, 4800.00, "Annual State Budget provision approved by State Cabinet for FY 2026-27."),
            ("TXN-FIN-2026-002", "AUTHORIZATION", dept_objs.get("Health & Family Welfare"), None, 950.00, "Departmental budget authorization issued to Health & Family Welfare."),
            ("TXN-FIN-2026-003", "AUTHORIZATION", dept_objs.get("School Education"), None, 1000.00, "Departmental budget authorization issued to School Education."),
            ("TXN-FIN-2026-004", "ALLOCATION", dept_objs.get("Public Works Department"), dist_objs.get("Nalanda"), 150.00, "District infrastructure allocation for Nalanda PWD road works."),
            ("TXN-FIN-2026-005", "RELEASE", dept_objs.get("Water & Sanitation (Jal Jeevan Mission)"), dist_objs.get("Patna"), 240.00, "Fund release for Jal Jeevan Mission pipe water supply in Patna district."),
        ]

        for tx_id, etype, dept_obj, dist_obj, amt, rem in ledger_entries:
            FinancialLedgerEntry.objects.get_or_create(
                transaction_id=tx_id,
                defaults={
                    "financial_year": "2026-27",
                    "entry_type": etype,
                    "department": dept_obj,
                    "district": dist_obj,
                    "amount_cr": amt,
                    "remarks": rem,
                }
            )

        self.stdout.write(self.style.SUCCESS("Successfully seeded State Governance Budget & Finance Data!"))
