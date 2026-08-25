from django.test import TestCase, Client
from rest_framework.test import APIClient
from rest_framework import status
from myapp.models import State, District, Block, Department, User, Facility, Role, PriorityLocation, DepartmentIndicator, EducationFacilityIndicator, WaterFacilityIndicator, RoadIndicator


class NDISModelAndPageTests(TestCase):
    def setUp(self):
        self.state = State.objects.create(name="Bihar")
        self.district = District.objects.create(state=self.state, name="Nalanda")
        self.department = Department.objects.create(name="Health")
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password123"
        )
        self.facility = Facility.objects.create(
            name="District Hospital",
            district=self.district,
            department=self.department
        )

    def test_index_page(self):
        client = Client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_admin_access(self):
        client = Client()
        client.force_login(self.user)
        response = client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        response = client.get("/admin/myapp/facility/")
        self.assertEqual(response.status_code, 200)

    def test_facility_district_name_filtering(self):
        client = APIClient()
        res1 = client.get("/api/facilities/?district=nalanda")
        self.assertEqual(res1.status_code, 200)
        self.assertGreaterEqual(len(res1.data), 1)

        res2 = client.get("/api/facilities/?distict=Nalanda")
        self.assertEqual(res2.status_code, 200)
        self.assertGreaterEqual(len(res2.data), 1)


class AuthenticationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.signup_url = "/api/auth/signup/"
        self.login_url = "/api/auth/login/"
        self.me_url = "/api/auth/me/"
        self.refresh_url = "/api/auth/token/refresh/"

        from myapp.models import Role
        self.role = Role.objects.create(name="Department Officer", code="DEPARTMENT_OFFICER")

        self.user_data = {
            "username": "john_doe",
            "email": "john@example.com",
            "password": "SecurePassword123!",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "9876543210",
            "designation": "Engineer",
            "role": self.role.id,
        }

    def test_signup_missing_role(self):
        data_without_role = self.user_data.copy()
        del data_without_role["role"]
        response = self.client.post(self.signup_url, data_without_role, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("role", response.data)

    def test_signup_success(self):
        response = self.client.post(self.signup_url, self.user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("user", response.data)
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])
        self.assertEqual(response.data["user"]["username"], "john_doe")

    def test_citizen_signup_success(self):
        from myapp.models import Role
        citizen_role = Role.objects.create(name="Registered Citizen", code="CITIZEN_REGISTERED", scope_level="SELF")
        citizen_data = {
            "username": "citizen_user",
            "email": "citizen@example.com",
            "password": "SecurePassword123!",
            "role": "CITIZEN_REGISTERED"
        }
        response = self.client.post(self.signup_url, citizen_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["role_info"]["code"], "CITIZEN_REGISTERED")
        self.assertIsNone(response.data["user"]["department"])
        self.assertEqual(response.data["user"]["designation"], "")

    def test_signup_duplicate_username(self):
        self.client.post(self.signup_url, self.user_data, format="json")
        duplicate_data = self.user_data.copy()
        duplicate_data["email"] = "different@example.com"
        response = self.client.post(self.signup_url, duplicate_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_signup_duplicate_email(self):
        self.client.post(self.signup_url, self.user_data, format="json")
        duplicate_data = self.user_data.copy()
        duplicate_data["username"] = "different_user"
        response = self.client.post(self.signup_url, duplicate_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_login_with_username_success(self):
        self.client.post(self.signup_url, self.user_data, format="json")
        login_data = {"username": "john_doe", "password": "SecurePassword123!"}
        response = self.client.post(self.login_url, login_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])

    def test_login_with_email_success(self):
        self.client.post(self.signup_url, self.user_data, format="json")
        login_data = {"username": "john@example.com", "password": "SecurePassword123!"}
        response = self.client.post(self.login_url, login_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", response.data)
        self.assertEqual(response.data["user"]["username"], "john_doe")

    def test_login_invalid_credentials(self):
        self.client.post(self.signup_url, self.user_data, format="json")
        login_data = {"username": "john_doe", "password": "WrongPassword!"}
        response = self.client.post(self.login_url, login_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_profile_authenticated(self):
        signup_res = self.client.post(self.signup_url, self.user_data, format="json")
        access_token = signup_res.data["tokens"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "john_doe")

    def test_user_profile_unauthenticated(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh(self):
        signup_res = self.client.post(self.signup_url, self.user_data, format="json")
        refresh_token = signup_res.data["tokens"]["refresh"]
        response = self.client.post(self.refresh_url, {"refresh": refresh_token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)


class ComplaintSystemTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.state = State.objects.create(name="Bihar")
        self.district = District.objects.create(state=self.state, name="Nalanda")
        self.department = Department.objects.create(name="Health Department")
        self.water_dept = Department.objects.create(name="Water Resources Department")

        from myapp.models import Role, ComplaintCategory, ComplaintPriority
        self.citizen_role = Role.objects.create(name="Citizen", code="CITIZEN_REGISTERED")
        self.officer_role = Role.objects.create(name="Department Officer", code="DEPARTMENT_OFFICER")

        self.citizen = User.objects.create_user(
            username="citizen_sunita",
            email="sunita@example.com",
            password="password123",
            role=self.citizen_role,
            first_name="Sunita",
            last_name="Devi"
        )
        self.officer = User.objects.create_user(
            username="officer_rahul",
            email="rahul@example.com",
            password="password123",
            role=self.officer_role,
            department=self.water_dept,
            first_name="Rahul",
            last_name="Kumar"
        )

        self.category = ComplaintCategory.objects.create(
            name="Broken Handpump / Borewell Defect",
            department=self.water_dept,
            default_priority=ComplaintPriority.HIGH,
            default_sla_hours=24
        )

    def test_create_and_auto_route_complaint(self):
        self.client.force_authenticate(user=self.citizen)
        payload = {
            "title": "Broken Handpump at Rajgir Ward 02",
            "description": "Handpump broken since last 3 days.",
            "category": self.category.id,
            "latitude": 25.0300,
            "longitude": 85.4200,
            "district": self.district.id
        }
        res = self.client.post("/api/complaints/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("tracking_no", res.data)
        self.assertEqual(res.data["department_name"], "Water Resources Department")
        self.assertEqual(res.data["status"], "SUBMITTED")

    def test_complaint_creation_latitude_longitude_typos(self):
        self.client.force_authenticate(user=self.citizen)
        payload = {
            "title": "Broken Handpump",
            "description": "Handpump broken near main square.",
            "category": self.category.id,
            "latitute": "25.1967",
            "longitute": "85.5142",
            "district": self.district.id
        }
        res = self.client.post("/api/complaints/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["latitude"], 25.1967)
        self.assertEqual(res.data["longitude"], 85.5142)

    def test_complaint_workflow_lifecycle(self):
        # 1. Create
        self.client.force_authenticate(user=self.citizen)
        payload = {
            "title": "Water Leakage",
            "description": "Piped water leakage near main road.",
            "category": self.category.id,
            "district": self.district.id
        }
        res_create = self.client.post("/api/complaints/", payload, format="json")
        cmp_id = res_create.data["id"]

        # 2. Assign to Officer
        self.client.force_authenticate(user=self.officer)
        res_assign = self.client.post(f"/api/complaints/{cmp_id}/assign/", {"target_user_id": self.officer.id, "remarks": "Assigned to Rahul"}, format="json")
        self.assertEqual(res_assign.status_code, status.HTTP_200_OK)
        self.assertEqual(res_assign.data["status"], "ASSIGNED")

        # 3. Accept
        res_accept = self.client.post(f"/api/complaints/{cmp_id}/accept/", {"remarks": "Accepted task"}, format="json")
        self.assertEqual(res_accept.status_code, status.HTTP_200_OK)
        self.assertEqual(res_accept.data["status"], "ACCEPTED")

        # 4. Resolve
        res_resolve = self.client.post(f"/api/complaints/{cmp_id}/resolve/", {"resolution_summary": "Fixed broken valve."}, format="json")
        self.assertEqual(res_resolve.status_code, status.HTTP_200_OK)
        self.assertEqual(res_resolve.data["status"], "RESOLVED")

        # 5. Timeline audit log
        res_timeline = self.client.get(f"/api/complaints/{cmp_id}/timeline/")
        self.assertEqual(res_timeline.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res_timeline.data), 4)


class DashboardSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        from myapp.models import Role
        self.citizen_role = Role.objects.create(name="Citizen", code="CITIZEN")
        self.officer_role = Role.objects.create(name="Department Officer", code="DEPARTMENT_OFFICER")
        self.dm_role = Role.objects.create(name="District Magistrate", code="DISTRICT_MAGISTRATE")

        self.citizen_user = User.objects.create_user(username="citizen1", password="password123", role=self.citizen_role)
        self.officer_user = User.objects.create_user(username="officer1", password="password123", role=self.officer_role)
        self.dm_user = User.objects.create_user(username="dm1", password="password123", role=self.dm_role)

    def test_citizen_dashboard_access(self):
        self.client.force_authenticate(user=self.citizen_user)
        res = self.client.get("/api/dashboards/citizen/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["role"], "CITIZEN")

    def test_citizen_forbidden_on_executive_dashboards(self):
        self.client.force_authenticate(user=self.citizen_user)
        
        # Citizen hitting Department Dashboard -> 403
        res_dept = self.client.get("/api/dashboards/department/")
        self.assertEqual(res_dept.status_code, status.HTTP_403_FORBIDDEN)

        # Citizen hitting District Dashboard -> 403
        res_dist = self.client.get("/api/dashboards/district/")
        self.assertEqual(res_dist.status_code, status.HTTP_403_FORBIDDEN)

        # Citizen hitting State Dashboard -> 403
        res_state = self.client.get("/api/dashboards/state/")
        self.assertEqual(res_state.status_code, status.HTTP_403_FORBIDDEN)

    def test_dm_executive_dashboard_access(self):
        self.client.force_authenticate(user=self.dm_user)
        res = self.client.get("/api/dashboards/district/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["role"], "DISTRICT_MAGISTRATE")

    def test_my_dashboard_unified_redirect(self):
        # 1. Citizen unified dashboard
        self.client.force_authenticate(user=self.citizen_user)
        res_c = self.client.get("/api/dashboards/my-dashboard/")
        self.assertEqual(res_c.status_code, status.HTTP_200_OK)
        self.assertEqual(res_c.data["role"], "CITIZEN")

        # 2. DM unified dashboard
        self.client.force_authenticate(user=self.dm_user)
        res_dm = self.client.get("/api/dashboards/my-dashboard/")
        self.assertEqual(res_dm.status_code, status.HTTP_200_OK)
        self.assertEqual(res_dm.data["role"], "DISTRICT_MAGISTRATE")

    def test_department_complaints_endpoint(self):
        dept = Department.objects.create(name="Public Works Department")
        res = self.client.get(f"/api/department/{dept.id}/complain/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["department_id"], dept.id)
        self.assertEqual(res.data["department_name"], "Public Works Department")
        self.assertIn("total_complaints", res.data)
        self.assertIn("status_summary", res.data)
        self.assertIn("priority_summary", res.data)
        self.assertIn("complaints", res.data)

    def test_user_crud_and_department_wise_user_get(self):
        dept = Department.objects.create(name="Health Department Test")
        role = Role.objects.create(code="TEST_OFFICER_1", name="Test Officer 1", scope_level="DEPARTMENT")
        
        # 1. Create User via POST /api/users/
        self.client.force_authenticate(user=self.dm_user)
        payload = {
            "username": "health_officer_test_1",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "email": "healthtest1@example.com",
            "first_name": "Health",
            "last_name": "Officer",
            "phone": "9876543210",
            "department": dept.id,
            "role": role.id
        }
        res_create = self.client.post("/api/users/", payload, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        user_id = res_create.data["id"]

        # 2. Get Users by Department query param GET /api/users/?department=...
        res_dept = self.client.get(f"/api/users/?department={dept.id}")
        self.assertEqual(res_dept.status_code, status.HTTP_200_OK)
        self.assertTrue(any(u["id"] == user_id for u in res_dept.data))

        # 3. Get Department Users via GET /api/department/{department_id}/users/
        res_direct = self.client.get(f"/api/department/{dept.id}/users/")
        self.assertEqual(res_direct.status_code, status.HTTP_200_OK)
        self.assertEqual(res_direct.data["department_id"], dept.id)
        self.assertEqual(res_direct.data["total_users"], 1)

        # 4. Update User via PATCH /api/users/{id}/
        res_patch = self.client.patch(f"/api/users/{user_id}/", {"designation": "Chief Medical Officer"}, format="json")
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(res_patch.data["designation"], "Chief Medical Officer")

        # 5. Delete User via DELETE /api/users/{id}/
        res_del = self.client.delete(f"/api/users/{user_id}/")
        self.assertEqual(res_del.status_code, status.HTTP_204_NO_CONTENT)

    def test_spatial_query_engine_excel_presets(self):
        # Test 1: Nearest health facility finder query
        res1 = self.client.get("/api/spatial-query/?q=nearest health facility finder&lat=25.0319&lng=85.4164")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data["status"], "success")
        self.assertEqual(res1.data["query_info"]["matched_preset_title"], "Nearest health facility finder")

        # Test 2: Nearby drinking water source locator query
        res2 = self.client.get("/api/spatial-query/?q=nearby drinking water source locator&lat=25.0319&lng=85.4164")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data["status"], "success")
        self.assertEqual(res2.data["query_info"]["matched_preset_title"], "Nearby drinking water source locator")

        # Test 3: Unauthenticated/Citizen search for Government Administration query -> 403 Forbidden
        res3_citizen = self.client.get("/api/spatial-query/?q=block-wise health service gap&lat=25.0319&lng=85.4164")
        self.assertEqual(res3_citizen.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res3_citizen.data["status"], "permission_denied")

        # Test 4: Authenticated Admin search for Government Administration & Line Department queries -> 200 OK
        admin_user = User.objects.create_superuser(username="spatial_admin", email="spatial_admin@example.com", password="password123")
        self.client.force_authenticate(user=admin_user)
        res3_admin = self.client.get("/api/spatial-query/?q=block-wise health service gap&lat=25.0319&lng=85.4164")
        self.assertEqual(res3_admin.status_code, status.HTTP_200_OK)
        self.assertEqual(res3_admin.data["query_info"]["perspective"], "Government Administration")

        res4_admin = self.client.get("/api/spatial-query/?q=institutions for rooftop solar install&lat=25.0319&lng=85.4164")
        self.assertEqual(res4_admin.status_code, status.HTTP_200_OK)
        self.assertEqual(res4_admin.data["query_info"]["perspective"], "Line Departments")

        # Test 5: Listing all presets grouped by perspective
        res5 = self.client.get("/api/spatial-query/")
        self.assertEqual(res5.status_code, status.HTTP_200_OK)
        self.assertIn("query_presets_by_perspective", res5.data)
        self.assertIn("citizens", res5.data["query_presets_by_perspective"])
        self.assertIn("government_administration", res5.data["query_presets_by_perspective"])
        self.assertIn("line_departments", res5.data["query_presets_by_perspective"])

        # Test 6: Department Head officer search for Line Department query -> 200 OK
        dept_role = Role.objects.create(name="Department Head", code="DEPARTMENT_HEAD")
        dept_user = User.objects.create_user(username="dept_head_user", email="dept_head@example.com", password="password123", role=dept_role)
        self.client.force_authenticate(user=dept_user)
        res6 = self.client.get("/api/spatial-query/?q=Groundwater stress and dependency zones&lat=25.0319&lng=85.4164")
        self.assertEqual(res6.status_code, status.HTTP_200_OK)
        self.assertEqual(res6.data["status"], "success")
        self.assertEqual(res6.data["query_info"]["matched_preset_title"], "Groundwater stress and dependency zones")


class ProposalDPRWizardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.state = State.objects.create(name="Bihar")
        self.district = District.objects.create(name="Nalanda", state=self.state)
        self.dept = Department.objects.create(name="Water & Sanitation (JJM)")
        self.user = User.objects.create_user(username="engineer_vijay", email="vijay@example.com", password="password123", district=self.district, department=self.dept)

    def test_planning_erp_dashboard_kpis(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get("/api/planning/dashboard/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "success")
        self.assertIn("kpi_summary", res.data)
        self.assertIn("suggested_development_needs", res.data)
        self.assertIn("dpr_repository", res.data)

    def test_dpr_wizard_7_steps_flow(self):
        self.client.force_authenticate(user=self.user)

        # 1. Create Initial Proposal
        create_payload = {
            "title": "Silao Ward 3 Elevated Reservoir",
            "category": "Infrastructure",
            "district": self.district.id,
            "department": self.dept.id,
            "priority": "high",
            "village": "Silao",
            "block": "Silao",
            "ward": "Ward 3",
            "population_impact": 15000,
            "gap_score": 8.5,
            "problem_statement": "Severe water shortage in peak summer."
        }
        res_create = self.client.post("/api/proposals/", create_payload, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        prop_id = res_create.data["id"]
        self.assertTrue(res_create.data["proposal_id"].startswith("PRP-"))
        self.assertEqual(res_create.data["block"], "Silao")

        # 3. Step 2: Survey & Inspection
        step2_payload = {
            "inspection_date": "2026-08-10",
            "survey_team": "Eng. Vijay Kumar, Inspector Ramesh",
            "inspection_notes": "Catchment area clear, site suitable for 500KL tank.",
            "gis_reference": "Selected site, Silao",
            "latitude": 25.0319,
            "longitude": 85.4164
        }
        res_step2 = self.client.post(f"/api/proposals/{prop_id}/step2-survey-inspection/", step2_payload, format="json")
        self.assertEqual(res_step2.status_code, status.HTTP_200_OK)

        # 4. Step 3: Technical DPR
        step3_payload = {
            "technical_scope": "Construction of 500KL RCC Over Head Tank with 4km DI pipeline.",
            "engineering_notes": "Requires land clearance from Circle Officer.",
            "estimated_timeline": "90 days"
        }
        res_step3 = self.client.post(f"/api/proposals/{prop_id}/step3-technical-dpr/", step3_payload, format="json")
        self.assertEqual(res_step3.status_code, status.HTTP_200_OK)

        # 5. Step 4: Financial Estimation
        step4_payload = {
            "civil_works": 8000000.00,
            "equipment_cost": 2000000.00,
            "electrical_cost": 1000000.00,
            "contingency_cost": 500000.00,
            "maintenance_cost": 500000.00,
            "delegated_power_note": "Within DM delegated power"
        }
        res_step4 = self.client.post(f"/api/proposals/{prop_id}/step4-financial-estimation/", step4_payload, format="json")
        self.assertEqual(res_step4.status_code, status.HTTP_200_OK)
        self.assertEqual(res_step4.data["grand_total"], 12000000.00)
        self.assertEqual(res_step4.data["cost_formatted"], "₹1.2 Cr")

        # 6. Step 5: Clearances
        step5_payload = {
            "clearances": {"environmental": "cleared", "land_acquisition": "in_progress"}
        }
        res_step5 = self.client.post(f"/api/proposals/{prop_id}/step5-clearances/", step5_payload, format="json")
        self.assertEqual(res_step5.status_code, status.HTTP_200_OK)

        # 7. Step 6: Attachments
        step6_payload = {
            "attachment_url": "http://127.0.0.1:8000/media/dpr_drawings.pdf"
        }
        res_step6 = self.client.post(f"/api/proposals/{prop_id}/step6-attachments/", step6_payload, format="json")
        self.assertEqual(res_step6.status_code, status.HTTP_200_OK)

        # 8. Step 7: Submit Proposal
        res_submit = self.client.post(f"/api/proposals/{prop_id}/submit/")
        self.assertEqual(res_submit.status_code, status.HTTP_200_OK)
        self.assertEqual(res_submit.data["proposal"]["status"], "PENDING_REVIEW")

        # 9. Sanction Proposal
        res_sanction = self.client.post(f"/api/proposals/{prop_id}/sanction/", {"sanctioned_amount": 12000000.00}, format="json")
        self.assertEqual(res_sanction.status_code, status.HTTP_200_OK)
        self.assertEqual(res_sanction.data["proposal"]["status"], "SANCTIONED")


class ProjectExecutionAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="engineer1", password="password123")
        self.client.force_authenticate(user=self.user)
        self.state = State.objects.create(name="Bihar")
        self.district = District.objects.create(state=self.state, name="Nalanda")
        self.department = Department.objects.create(name="Water Resources Department")

    def test_project_crud_and_summary(self):
        # 1. Create Project
        payload = {
            "title": "Surajpur Ward 3 Elevated Water Reservoir",
            "sanction_amount": 12000000.00,
            "expenditure_amount": 11400000.00,
            "progress_percentage": 100.00,
            "status": "completed",
            "risk_level": "high",
            "block": "Surajpur"
        }
        res_create = self.client.post("/api/projects/", payload, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        prj_id = res_create.data["id"]

        # 2. Get Summary KPIs
        res_summary = self.client.get("/api/projects/summary/")
        self.assertEqual(res_summary.status_code, status.HTTP_200_OK)
        self.assertEqual(res_summary.data["completed"], 1)

        # 3. Post Daily Progress Action
        progress_payload = {
            "progress_percentage": 100.00,
            "work_description": "Final concrete inspection complete",
            "risk_signal": "Waterlogging issue resolved",
            "severity": "medium"
        }
        res_daily = self.client.post(f"/api/projects/{prj_id}/daily-progress/", progress_payload, format="json")
        self.assertEqual(res_daily.status_code, status.HTTP_200_OK)

        # 4. List Site Diaries, MBs, Bills & Risks
        res_diaries = self.client.get(f"/api/site-diaries/?project={prj_id}")
        self.assertEqual(res_diaries.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res_diaries.data), 1)

    def test_proposal_auto_becomes_project_and_project_get_endpoint(self):
        # 1. Create a draft proposal (DRAFT_DPR)
        create_payload = {
            "title": "Road Construction Silao Block",
            "category": "Infrastructure",
            "district": self.district.id,
            "department": self.department.id,
            "block": "Silao",
            "estimated_cost": 5000000.00
        }
        res_prop = self.client.post("/api/proposals/", create_payload, format="json")
        self.assertEqual(res_prop.status_code, status.HTTP_201_CREATED)
        prop_id = res_prop.data["id"]

        # 2. Verify DRAFT_DPR proposal does NOT show in /api/project/
        res_draft_check = self.client.get("/api/project/")
        self.assertEqual(res_draft_check.status_code, status.HTTP_200_OK)
        draft_results = res_draft_check.data.get("results", res_draft_check.data) if isinstance(res_draft_check.data, dict) else res_draft_check.data
        self.assertFalse(any(p.get("proposal") == prop_id or (p.get("proposal_details") and p["proposal_details"]["id"] == prop_id) for p in draft_results))

        # 3. Sanction proposal
        res_sanction = self.client.post(f"/api/proposals/{prop_id}/sanction/", {"sanctioned_amount": 5000000.00}, format="json")
        self.assertEqual(res_sanction.status_code, status.HTTP_200_OK)

        # 4. Verify SANCTIONED proposal NOW shows in GET /api/project/ and /api/projects/
        res_proj_singular = self.client.get("/api/project/")
        self.assertEqual(res_proj_singular.status_code, status.HTTP_200_OK)
        results = res_proj_singular.data.get("results", res_proj_singular.data) if isinstance(res_proj_singular.data, dict) else res_proj_singular.data
        self.assertTrue(any(p.get("proposal") == prop_id or (p.get("proposal_details") and p["proposal_details"]["id"] == prop_id) for p in results))

        res_proj_plural = self.client.get("/api/projects/")
        self.assertEqual(res_proj_plural.status_code, status.HTTP_200_OK)
        results_plural = res_proj_plural.data.get("results", res_proj_plural.data) if isinstance(res_proj_plural.data, dict) else res_proj_plural.data
        self.assertTrue(any(p.get("proposal") == prop_id or (p.get("proposal_details") and p["proposal_details"]["id"] == prop_id) for p in results_plural))

    def test_spatial_query_strict_radius_and_keyword_matching(self):
        # 1. Test searching "nearby bank me" does not fall back to Blood_Bank or Hospital when no financial bank exists
        res_bank = self.client.get("/api/spatial-query/?q=nearby bank me&lat=30.3165&lng=78.0322&radius=10&limit=3")
        self.assertEqual(res_bank.status_code, status.HTTP_200_OK)
        self.assertEqual(res_bank.data["total_found"], 0)
        self.assertEqual(len(res_bank.data["results"]), 0)

        # 2. Test searching "nearby water me" with radius=10 does not return results 891 km away
        res_water = self.client.get("/api/spatial-query/?q=nearby water me&lat=30.3165&lng=78.0322&radius=10&limit=3")
        self.assertEqual(res_water.status_code, status.HTTP_200_OK)
        self.assertEqual(res_water.data["total_found"], 0)
        self.assertEqual(len(res_water.data["results"]), 0)

    def test_proposal_negotiation_flow_and_direct_approval(self):
        # 1. Create a proposal
        create_payload = {
            "title": "Nalanda Solar Plant Installation",
            "category": "Energy",
            "district": self.district.id,
            "department": self.department.id,
            "block": "Biharsharif",
            "estimated_cost": 10000000.00
        }
        res_prop = self.client.post("/api/proposals/", create_payload, format="json")
        self.assertEqual(res_prop.status_code, status.HTTP_201_CREATED)
        prop_id = res_prop.data["id"]

        # 2. DM initiates negotiation / counter-offer on price & timeline
        neg_payload = {
            "action": "COUNTER_OFFER",
            "proposed_amount": 8500000.00,
            "proposed_timeline_days": 60,
            "scope": "Revised scope to 500KW panel capacity",
            "remarks": "Please reduce budget and completion timeline"
        }
        res_neg = self.client.post(f"/api/proposals/{prop_id}/negotiation/", neg_payload, format="json")
        self.assertEqual(res_neg.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_neg.data["proposal"]["status"], "UNDER_NEGOTIATION")

        # 3. Verify negotiations list endpoint
        res_history = self.client.get(f"/api/proposal-negotiations/?proposal={prop_id}")
        self.assertEqual(res_history.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_history.data), 1)
        self.assertEqual(float(res_history.data[0]["proposed_amount"]), 8500000.00)

        # 4. Department Head accepts counter offer
        accept_payload = {
            "action": "ACCEPT",
            "remarks": "Agreed to revised amount and timeline"
        }
        res_accept = self.client.post(f"/api/proposals/{prop_id}/negotiation/", accept_payload, format="json")
        self.assertEqual(res_accept.status_code, status.HTTP_200_OK)
        self.assertEqual(res_accept.data["proposal"]["status"], "APPROVED")

        # 5. DM sanctions approved proposal -> Project auto-created!
        res_sanction = self.client.post(f"/api/proposals/{prop_id}/sanction/", {"sanctioned_amount": 8500000.00}, format="json")
        self.assertEqual(res_sanction.status_code, status.HTTP_200_OK)
        self.assertEqual(res_sanction.data["proposal"]["status"], "SANCTIONED")

        # Verify project list contains the auto-created project
        res_proj = self.client.get("/api/project/")
        self.assertEqual(res_proj.status_code, status.HTTP_200_OK)
        results = res_proj.data.get("results", res_proj.data) if isinstance(res_proj.data, dict) else res_proj.data
        self.assertTrue(any(p.get("proposal") == prop_id or (p.get("proposal_details") and p["proposal_details"]["id"] == prop_id) for p in results))

    def test_proposal_negotiation_multi_round_spec(self):
        # 1. Create a proposal with original estimated_cost = 80,000,000 (₹8 Cr)
        create_payload = {
            "title": "Nalanda 100-Bed Sub-Divisional Hospital",
            "category": "Healthcare",
            "district": self.district.id,
            "department": self.department.id,
            "block": "Rajgir",
            "estimated_cost": 80000000.00
        }
        res_prop = self.client.post("/api/proposals/", create_payload, format="json")
        self.assertEqual(res_prop.status_code, status.HTTP_201_CREATED)
        prop_id = res_prop.data["id"]

        # 2. Validation test: Amount > estimated_cost (₹9 Cr > ₹8 Cr) must be rejected
        res_invalid = self.client.post(f"/api/proposals/{prop_id}/negotiation/", {
            "action": "COUNTER_OFFER",
            "proposed_amount": 90000000.00,
            "remarks": "Excessive amount test"
        }, format="json")
        self.assertEqual(res_invalid.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. Round 1: DM sends counter offer (₹7 Cr)
        res_r1 = self.client.post(f"/api/proposals/{prop_id}/negotiation/", {
            "action": "COUNTER_OFFER",
            "proposed_amount": 70000000.00,
            "proposed_timeline_days": 330,
            "proposed_scope": "100-bed hospital without staff quarters",
            "remarks": "Budget optimization required"
        }, format="json")
        self.assertEqual(res_r1.status_code, status.HTTP_201_CREATED)

        # 4. Round 2: Department Head responds with counter offer (₹6.5 Cr)
        res_r2 = self.client.post(f"/api/proposals/{prop_id}/negotiation-response/", {
            "action": "COUNTER_OFFER",
            "proposed_amount": 65000000.00,
            "proposed_timeline_days": 300,
            "proposed_scope": "100-bed hospital with basic OPD quarters",
            "remarks": "Revised estimate"
        }, format="json")
        self.assertEqual(res_r2.status_code, status.HTTP_201_CREATED)

        # 5. Round 3: DM sends final counter offer (₹6 Cr)
        res_r3 = self.client.post(f"/api/proposals/{prop_id}/negotiation/", {
            "action": "COUNTER_OFFER",
            "proposed_amount": 60000000.00,
            "proposed_timeline_days": 270,
            "proposed_scope": "100-bed hospital standard layout",
            "remarks": "Final offer"
        }, format="json")
        self.assertEqual(res_r3.status_code, status.HTTP_201_CREATED)

        # 6. Round 4: Department Head ACCEPTS ₹6 Cr
        res_accept = self.client.post(f"/api/proposals/{prop_id}/negotiation-response/", {
            "action": "ACCEPT",
            "proposed_amount": 60000000.00,
            "remarks": "Revised amount accepted"
        }, format="json")
        self.assertEqual(res_accept.status_code, status.HTTP_200_OK)

        # 7. CRITICAL VERIFICATION:
        # Proposal estimated_cost must remain ₹8 Cr (80,000,000) for audit/history
        # Proposal agreed_amount must be ₹6 Cr (60,000,000)
        # Proposal approval_mode must be "NEGOTIATED"
        res_prop_get = self.client.get(f"/api/proposals/{prop_id}/")
        self.assertEqual(res_prop_get.status_code, status.HTTP_200_OK)
        self.assertEqual(float(res_prop_get.data["estimated_cost"]), 80000000.00)
        self.assertEqual(float(res_prop_get.data["agreed_amount"]), 60000000.00)
        self.assertEqual(res_prop_get.data["approval_mode"], "NEGOTIATED")
        self.assertEqual(res_prop_get.data["status"], "APPROVED")

        # 8. GET /api/proposals/{id}/negotiations/ history check
        res_history = self.client.get(f"/api/proposals/{prop_id}/negotiations/")
        self.assertEqual(res_history.status_code, status.HTTP_200_OK)
        self.assertEqual(res_history.data["estimated_cost"], "80000000.00")
        self.assertEqual(res_history.data["agreed_amount"], "60000000.00")
        self.assertEqual(res_history.data["approval_mode"], "NEGOTIATED")
        self.assertGreaterEqual(len(res_history.data["history"]), 4)

    def test_one_time_fund_release(self):
        create_payload = {
            "title": "Road Overbridge Silao",
            "category": "Infrastructure",
            "district": self.district.id,
            "department": self.department.id,
            "estimated_cost": 5000000.00
        }
        res_prop = self.client.post("/api/proposals/", create_payload, format="json")
        prop_id = res_prop.data["id"]

        # Sanction
        self.client.post(f"/api/proposals/{prop_id}/sanction/", {"sanctioned_amount": 5000000.00}, format="json")

        # One-time Full Release
        rel_payload = {
            "release_type": "FULL",
            "amount": 5000000.00,
            "release_order_no": "REL-2026-FULL-01",
            "description": "Full budget one-time release"
        }
        res_rel = self.client.post(f"/api/proposals/{prop_id}/release/", rel_payload, format="json")
        self.assertEqual(res_rel.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_rel.data["release_summary"]["release_status"], "FULLY_RELEASED")
        self.assertEqual(res_rel.data["proposal"]["status"], "FUNDS_RELEASED")

        # Attempting additional release after FULL release must fail with HTTP 400
        res_invalid = self.client.post(f"/api/proposals/{prop_id}/release/", {
            "release_type": "INSTALLMENT",
            "amount": 200000.00
        }, format="json")
        self.assertEqual(res_invalid.status_code, status.HTTP_400_BAD_REQUEST)

    def test_installment_wise_fund_release(self):
        create_payload = {
            "title": "Super Specialty Hospital Block",
            "category": "Healthcare",
            "district": self.district.id,
            "department": self.department.id,
            "estimated_cost": 10000000.00
        }
        res_prop = self.client.post("/api/proposals/", create_payload, format="json")
        prop_id = res_prop.data["id"]

        # Sanction
        self.client.post(f"/api/proposals/{prop_id}/sanction/", {"sanctioned_amount": 10000000.00}, format="json")

        # Installment 1: 30% (₹30 Lakhs)
        inst1_payload = {
            "release_type": "INSTALLMENT",
            "amount": 3000000.00,
            "installment_name": "1st Tranche (30%)",
            "release_order_no": "REL-INST-01"
        }
        res_inst1 = self.client.post(f"/api/proposals/{prop_id}/release/", inst1_payload, format="json")
        self.assertEqual(res_inst1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_inst1.data["release_summary"]["release_status"], "PARTIALLY_RELEASED")
        self.assertEqual(float(res_inst1.data["release_summary"]["remaining_balance"]), 7000000.00)

        # Attempting to switch release_type to FULL midway must fail with HTTP 400
        res_switch_invalid = self.client.post(f"/api/proposals/{prop_id}/release/", {
            "release_type": "FULL",
            "amount": 7000000.00
        }, format="json")
        self.assertEqual(res_switch_invalid.status_code, status.HTTP_400_BAD_REQUEST)

        # Installment 2: Remaining 70% (₹70 Lakhs)
        inst2_payload = {
            "release_type": "INSTALLMENT",
            "amount": 7000000.00,
            "installment_name": "2nd Final Tranche (70%)",
            "release_order_no": "REL-INST-02"
        }
        res_inst2 = self.client.post(f"/api/proposals/{prop_id}/release/", inst2_payload, format="json")
        self.assertEqual(res_inst2.status_code, status.HTTP_200_OK)
        self.assertEqual(res_inst2.data["release_summary"]["release_status"], "FULLY_RELEASED")
        self.assertEqual(float(res_inst2.data["release_summary"]["remaining_balance"]), 0.00)

        # GET history check
        res_releases = self.client.get(f"/api/proposals/{prop_id}/releases/")
        self.assertEqual(res_releases.status_code, status.HTTP_200_OK)
        self.assertEqual(res_releases.data["total_installments"], 2)

    def test_complete_project_lifecycle_workflow(self):
        # 1. Dept Head Creates Proposal
        res_prop = self.client.post("/api/proposals/", {
            "title": "Integrated Community Healthcare Center",
            "category": "Healthcare",
            "district": self.district.id,
            "department": self.department.id,
            "estimated_cost": 20000000.00
        }, format="json")
        prop_id = res_prop.data["id"]

        # 2. Submit to DM
        self.client.post(f"/api/proposals/{prop_id}/submit/", {}, format="json")

        # 3. DM Counter Offer & Agreement (Agreed Amount = ₹1.8 Cr)
        self.client.post(f"/api/proposals/{prop_id}/negotiation/", {
            "action": "COUNTER_OFFER",
            "proposed_amount": 18000000.00,
            "remarks": "Counter offer ₹1.8 Cr"
        }, format="json")
        self.client.post(f"/api/proposals/{prop_id}/negotiation/", {
            "action": "ACCEPT",
            "remarks": "Accepted ₹1.8 Cr"
        }, format="json")

        # 4. DM Sanction Budget
        self.client.post(f"/api/proposals/{prop_id}/sanction/", {"sanctioned_amount": 18000000.00}, format="json")

        # 5. Fund Release (Full Release)
        self.client.post(f"/api/proposals/{prop_id}/release/", {
            "release_type": "FULL",
            "amount": 18000000.00,
            "release_order_no": "REL-WORKFLOW-01"
        }, format="json")

        # Get linked ProjectExecution
        res_projects = self.client.get("/api/projects/")
        self.assertEqual(res_projects.status_code, status.HTTP_200_OK)
        proj_list = res_projects.data["results"] if "results" in res_projects.data else res_projects.data
        proj_item = [p for p in proj_list if p["title"] == "Integrated Community Healthcare Center"][0]
        proj_id = proj_item["id"]

        # 6. Dept Head Assigns Work
        res_assign = self.client.post(f"/api/projects/{proj_id}/assign-work/", {
            "contractor_name": "ABC Infra Ltd",
            "assignment_notes": "Priority healthcare construction work assigned"
        }, format="json")
        self.assertEqual(res_assign.status_code, status.HTTP_200_OK)
        self.assertEqual(res_assign.data["project"]["contractor_name"], "ABC Infra Ltd")

        # 7. Field Engineers Log Daily Progress (100%), Site Diary, e-MB
        self.client.post(f"/api/projects/{proj_id}/daily-progress/", {
            "progress_percentage": 100.0,
            "labour_count": 45,
            "materials_used": "Cement 500 bags, Steel 12 Tons",
            "weather_condition": "CLEAR",
            "diary_notes": "All civil and structural work completed 100%"
        }, format="json")

        self.client.post("/api/measurement-books/", {
            "project": proj_id,
            "item_description": "Structural RCC Work and Finishings",
            "unit_of_measurement": "Sqm",
            "measured_quantity": 1200.0,
            "rate": 15000.0,
            "total_amount": 18000000.0,
            "status": "verified"
        }, format="json")

        # 8. Department Officer Field Work Review
        res_off_rev = self.client.post(f"/api/projects/{proj_id}/officer-review/", {
            "officer_review_status": "APPROVED",
            "remarks": "Field site inspection completed, MB verified 100% accurate."
        }, format="json")
        self.assertEqual(res_off_rev.status_code, status.HTTP_200_OK)
        self.assertEqual(res_off_rev.data["project"]["officer_review_status"], "APPROVED")

        # 9. Department Head Final Verification & Completion
        res_verify = self.client.post(f"/api/projects/{proj_id}/verify-completion/", {
            "verification_status": "APPROVED",
            "remarks": "Project completion verified by Department Head."
        }, format="json")
        self.assertEqual(res_verify.status_code, status.HTTP_200_OK)
        self.assertEqual(res_verify.data["project"]["status"], "completed")
        self.assertEqual(res_verify.data["verification_summary"]["verification_status"], "APPROVED")

    def test_budget_utilization_module(self):
        # Create Proposal, Sanction ₹1.5 Cr, Release ₹1.5 Cr
        res_prop = self.client.post("/api/proposals/", {
            "title": "Sub Division Water Supply Project",
            "category": "Infrastructure",
            "district": self.district.id,
            "department": self.department.id,
            "estimated_cost": 15000000.00
        }, format="json")
        prop_id = res_prop.data["id"]

        self.client.post(f"/api/proposals/{prop_id}/sanction/", {"sanctioned_amount": 15000000.00}, format="json")
        self.client.post(f"/api/proposals/{prop_id}/release/", {"release_type": "FULL", "amount": 15000000.00}, format="json")

        res_projects = self.client.get("/api/projects/")
        proj_list = res_projects.data["results"] if "results" in res_projects.data else res_projects.data
        proj_item = [p for p in proj_list if p["title"] == "Sub Division Water Supply Project"][0]
        proj_id = proj_item["id"]

        # Create DEPARTMENT_OFFICER user in same department
        officer_role, _ = Role.objects.get_or_create(code="DEPARTMENT_OFFICER", name="Department Officer")
        dept_officer = User.objects.create_user(
            username="dept_officer_test",
            email="dept_officer@test.com",
            password="Password123!",
            role=officer_role,
            department=self.department
        )

        # Force authenticate as DEPARTMENT_OFFICER
        self.client.force_authenticate(user=dept_officer)

        # 1. Invalid Amount (<= 0)
        res_inv_amt = self.client.post(f"/api/projects/{proj_id}/expenditure/", {
            "amount": 0.00,
            "reference_no": "EXP-INV-01"
        }, format="json")
        self.assertEqual(res_inv_amt.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Record Tranche 1 Expenditure: ₹50 Lakhs (33.33%)
        res_exp1 = self.client.post(f"/api/projects/{proj_id}/expenditure/", {
            "amount": "5000000.00",
            "expenditure_date": "2026-08-18",
            "expense_type": "CIVIL_WORK",
            "reference_no": "EXP-PRJ-001",
            "remarks": "Civil foundation work expenditure verified against MB."
        }, format="json")
        self.assertEqual(res_exp1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_exp1.data["budget_summary"]["utilized_amount"], 5000000.00)
        self.assertEqual(res_exp1.data["budget_summary"]["remaining_amount"], 10000000.00)

        # 3. Duplicate Reference No Check
        res_dup = self.client.post(f"/api/projects/{proj_id}/expenditure/", {
            "amount": "1000000.00",
            "reference_no": "EXP-PRJ-001"
        }, format="json")
        self.assertEqual(res_dup.status_code, status.HTTP_400_BAD_REQUEST)

        # 4. Record Tranche 2 Expenditure: ₹1.0 Cr (Cumulative ₹1.5 Cr = 100%)
        res_exp2 = self.client.post(f"/api/projects/{proj_id}/expenditure/", {
            "amount": "10000000.00",
            "expenditure_date": "2026-08-18",
            "expense_type": "MATERIAL",
            "reference_no": "EXP-PRJ-002",
            "remarks": "Piping & equipment material supply expenditure verified."
        }, format="json")
        self.assertEqual(res_exp2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_exp2.data["budget_summary"]["utilization_status"], "FULLY_UTILIZED")
        self.assertEqual(res_exp2.data["budget_summary"]["remaining_amount"], 0.00)

        # 5. Over-expenditure Check (Cumulative > Released Amount)
        res_over = self.client.post(f"/api/projects/{proj_id}/expenditure/", {
            "amount": "500000.00",
            "reference_no": "EXP-PRJ-OVER"
        }, format="json")
        self.assertEqual(res_over.status_code, status.HTTP_400_BAD_REQUEST)

        # 6. GET Budget Utilization Summary Endpoint
        res_util = self.client.get(f"/api/projects/{proj_id}/budget-utilization/")
        self.assertEqual(res_util.status_code, status.HTTP_200_OK)
        self.assertEqual(float(res_util.data["utilized_amount"]), 15000000.00)
        self.assertEqual(float(res_util.data["remaining_amount"]), 0.00)
        self.assertEqual(res_util.data["utilization_percentage"], 100.0)
        self.assertEqual(res_util.data["utilization_status"], "FULLY_UTILIZED")
        self.assertEqual(res_util.data["total_transactions"], 2)

    def test_tiered_work_assignment_flow(self):
        # Create Project
        res_prop = self.client.post("/api/proposals/", {
            "title": "Tiered Assignment Test Hospital Project",
            "category": "Healthcare",
            "district": self.district.id,
            "department": self.department.id,
            "estimated_cost": 25000000.00
        }, format="json")
        prop_id = res_prop.data["id"]

        self.client.post(f"/api/proposals/{prop_id}/sanction/", {"sanctioned_amount": 25000000.00}, format="json")
        res_projects = self.client.get("/api/projects/")
        proj_list = res_projects.data["results"] if "results" in res_projects.data else res_projects.data
        proj_item = [p for p in proj_list if p["title"] == "Tiered Assignment Test Hospital Project"][0]
        proj_id = proj_item["id"]

        # Create Department Officer User
        officer_user = User.objects.create_user(
            username="dept_officer_tier1",
            email="officer_tier1@test.com",
            password="Password123!",
            department=self.department
        )

        # Create Junior Engineer User
        engineer_user = User.objects.create_user(
            username="je_engineer_tier2",
            email="je_tier2@test.com",
            password="Password123!",
            department=self.department
        )

        # LEVEL 1: Department Head Assigns Department Officer
        res_lvl1 = self.client.post(f"/api/projects/{proj_id}/assign-officer/", {
            "assigned_officer_id": officer_user.id,
            "assignment_notes": "Assigned to Nodal Dept Officer for healthcare supervision.",
            "target_completion_date": "2026-12-31"
        }, format="json")
        self.assertEqual(res_lvl1.status_code, status.HTTP_200_OK)
        self.assertEqual(res_lvl1.data["assignment_level"], "LEVEL_1_DEPARTMENT_HEAD_TO_OFFICER")
        self.assertEqual(res_lvl1.data["assigned_officer"]["id"], officer_user.id)

        # LEVEL 2: Department Officer Assigns Junior Engineer & Contractor
        res_lvl2 = self.client.post(f"/api/projects/{proj_id}/assign-engineer/", {
            "assigned_engineer_id": engineer_user.id,
            "contractor_name": "Nalanda Civil Infra Ltd",
            "field_assignment_notes": "JE assigned for daily site measurements & e-MB entry."
        }, format="json")
        self.assertEqual(res_lvl2.status_code, status.HTTP_200_OK)
        self.assertEqual(res_lvl2.data["assignment_level"], "LEVEL_2_OFFICER_TO_FIELD_ENGINEER")
        self.assertEqual(res_lvl2.data["contractor_name"], "Nalanda Civil Infra Ltd")
        self.assertEqual(res_lvl2.data["assigned_engineer_name"], "je_engineer_tier2")

    def test_ddss_dm_decision_dashboard_api(self):
        res = self.client.get("/api/ddss/dashboard/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "SUCCESS")
        self.assertEqual(res.data["dashboard_role"], "DISTRICT_MAGISTRATE_DDSS")
        self.assertIn("top_kpis", res.data)
        self.assertIn("health_snapshot", res.data)
        self.assertIn("action_queue", res.data)

    def test_ddss_compound_spatial_query_api(self):
        payload = {
            "target_layer": "villages",
            "spatial_filters": [{"type": "within_distance", "distance_km": 5}],
            "attribute_filters": [{"field": "population", "operator": ">=", "value": 1000}],
            "sort": [{"field": "priority_score", "direction": "desc"}],
            "limit": 10
        }
        res = self.client.post("/api/spatial-analysis/query/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["target_layer"], "villages")
        self.assertIn("geojson", res.data)
        self.assertEqual(res.data["geojson"]["type"], "FeatureCollection")

    def test_ddss_health_decision_workspace_apis(self):
        res_fac = self.client.get("/api/health/facilities/")
        self.assertEqual(res_fac.status_code, status.HTTP_200_OK)

        res_staff = self.client.get("/api/health/staffing/")
        self.assertEqual(res_staff.status_code, status.HTTP_200_OK)

        res_work = self.client.get("/api/health/workload/")
        self.assertEqual(res_work.status_code, status.HTTP_200_OK)

        res_infra = self.client.get("/api/health/infrastructure/")
        self.assertEqual(res_infra.status_code, status.HTTP_200_OK)

        res_med = self.client.get("/api/health/medicines/")
        self.assertEqual(res_med.status_code, status.HTTP_200_OK)

    def test_ddss_gap_and_priority_engine(self):
        res_gap = self.client.get("/api/gap-analysis/")
        self.assertEqual(res_gap.status_code, status.HTTP_200_OK)
        self.assertIn("model_version", res_gap.data)

        # Create Priority Location
        prio = PriorityLocation.objects.create(
            title="Test High Gap Health Sub-Centre",
            department=self.department,
            district=self.district,
            gap_score=84.5,
            priority="P1",
            recommended_action="Construct new Sub-Centre"
        )

        res_prio = self.client.get(f"/api/priority-locations/{prio.id}/")
        self.assertEqual(res_prio.status_code, status.HTTP_200_OK)
        self.assertEqual(res_prio.data["priority"], "P1")

    def test_ddss_geotag_exif_and_coordinate_validation(self):
        # Coordinate boundary validation
        res_coord = self.client.post("/api/gis/validate-coordinate/", {"latitude": 25.198, "longitude": 85.514}, format="json")
        self.assertEqual(res_coord.status_code, status.HTTP_200_OK)
        self.assertTrue(res_coord.data["inside_district"])

        # 25m Deduplication check
        res_dedup = self.client.post("/api/gis/check-duplicate/", {"latitude": 25.198, "longitude": 85.514}, format="json")
        self.assertEqual(res_dedup.status_code, status.HTTP_200_OK)
        self.assertIn("duplicate_warning", res_dedup.data)

        # EXIF Geotag Verification
        res_exif = self.client.post("/api/evidence/verify-geotag/", {"photo_path": "site_photo.jpg", "latitude": 25.198, "longitude": 85.514}, format="json")
        self.assertEqual(res_exif.status_code, status.HTTP_200_OK)
        self.assertIn("status", res_exif.data)

    def test_ddss_priority_to_dpr_proposal_linkage(self):
        prio = PriorityLocation.objects.create(
            title="Priority Location for DPR Linkage",
            department=self.department,
            district=self.district,
            gap_score=88.0,
            priority="P1"
        )

        res_link = self.client.post(f"/api/priority-locations/{prio.id}/create-proposal/", {"estimated_cost": 18000000.00}, format="json")
        self.assertEqual(res_link.status_code, status.HTTP_201_CREATED)
        self.assertIn("proposal_code", res_link.data)

        prio.refresh_from_db()
        self.assertIsNotNone(prio.linked_proposal)

    def test_multi_department_indicator_creation_and_api_filtering(self):
        dept_edu, _ = Department.objects.get_or_create(name="Education Department", defaults={"code": "EDUCATION"})
        dept_edu.code = "EDUCATION"
        dept_edu.save()

        dept_wtr, _ = Department.objects.get_or_create(name="Water Resources Department", defaults={"code": "WATER_RESOURCES"})
        dept_wtr.code = "WATER_RESOURCES"
        dept_wtr.save()

        dept_pwd, _ = Department.objects.get_or_create(name="Public Works Department", defaults={"code": "PWD"})
        dept_pwd.code = "PWD"
        dept_pwd.save()

        ind_edu = DepartmentIndicator.objects.create(
            department=dept_edu,
            district=self.district,
            indicator_code="TEACHER_VACANCY",
            indicator_name="Teacher Vacancy Count",
            value=28.0,
            unit="posts",
            period="2026-08",
            source="Education MIS"
        )
        ind_wtr = DepartmentIndicator.objects.create(
            department=dept_wtr,
            district=self.district,
            indicator_code="WATER_COVERAGE",
            indicator_name="Household Tap Water Coverage",
            value=65.5,
            unit="percent",
            period="2026-08",
            source="Jal Jeevan Mission"
        )
        ind_pwd = DepartmentIndicator.objects.create(
            department=dept_pwd,
            district=self.district,
            indicator_code="POOR_ROAD_LENGTH",
            indicator_name="Unpaved Poor Condition Road Length",
            value=14.2,
            unit="km",
            period="2026-08",
            source="PWD Survey"
        )

        # Test Department Code Filtering on /api/ddst/indicators/
        res_edu = self.client.get("/api/ddst/indicators/?department_code=EDUCATION")
        self.assertEqual(res_edu.status_code, status.HTTP_200_OK)
        results = res_edu.data.get("results") if isinstance(res_edu.data, dict) else res_edu.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["indicator_code"], "TEACHER_VACANCY")
        self.assertEqual(results[0]["department_code"], "EDUCATION")

        res_wtr = self.client.get("/api/ddst/indicators/?department_code=WATER_RESOURCES")
        self.assertEqual(res_wtr.status_code, status.HTTP_200_OK)
        results_wtr = res_wtr.data.get("results") if isinstance(res_wtr.data, dict) else res_wtr.data
        self.assertEqual(len(results_wtr), 1)
        self.assertEqual(results_wtr[0]["indicator_code"], "WATER_COVERAGE")

    def test_department_specific_dashboard_api(self):
        dept_edu, _ = Department.objects.get_or_create(name="Education Department", defaults={"code": "EDUCATION"})
        dept_edu.code = "EDUCATION"
        dept_edu.save()
        Facility.objects.create(name="Test High School Dashboard", department=dept_edu, district=self.district)
        res = self.client.get(f"/api/ddst/department/EDUCATION/dashboard/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "SUCCESS")
        self.assertEqual(res.data["department"]["code"], "EDUCATION")
        self.assertIn("kpis", res.data)
        self.assertIn("priority_locations", res.data)

        # Test Invalid Department Code
        res_inv = self.client.get("/api/ddst/department/NON_EXISTENT_DEPT/dashboard/")
        self.assertEqual(res_inv.status_code, status.HTTP_404_NOT_FOUND)

    def test_dm_dashboard_department_filter(self):
        dept_pwd, _ = Department.objects.get_or_create(name="Public Works Department", defaults={"code": "PWD"})
        dept_pwd.code = "PWD"
        dept_pwd.save()
        res_dm = self.client.get("/api/ddst/dashboard/?department_code=PWD")
        self.assertEqual(res_dm.status_code, status.HTTP_200_OK)
        self.assertEqual(res_dm.data["active_department_filter"]["code"], "PWD")

    def test_line_departments_list_api(self):
        res = self.client.get("/api/ddst/departments/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("departments", res.data)
        self.assertTrue(len(res.data["departments"]) > 0)

    def test_education_indicator_properties_and_calculation(self):
        dept_edu, _ = Department.objects.get_or_create(name="Education Department", defaults={"code": "EDUCATION"})
        dept_edu.code = "EDUCATION"
        dept_edu.save()
        fac_edu = Facility.objects.create(name="Test High School", department=dept_edu, district=self.district)
        edu_ind = EducationFacilityIndicator.objects.create(
            facility=fac_edu, sanctioned_teachers=20, available_teachers=14, student_enrolment=500
        )
        self.assertEqual(edu_ind.teacher_vacancies, 6)
        self.assertEqual(edu_ind.teacher_vacancy_percentage, 30.0)

    def test_water_facility_indicator_properties(self):
        dept_wtr, _ = Department.objects.get_or_create(name="Water Resources Department", defaults={"code": "WATER_RESOURCES"})
        dept_wtr.code = "WATER_RESOURCES"
        dept_wtr.save()
        fac_wtr = Facility.objects.create(name="Test Water Pump House", department=dept_wtr, district=self.district)
        wtr_ind = WaterFacilityIndicator.objects.create(
            facility=fac_wtr, household_coverage_percent=70.0, non_functional_sources_count=2, daily_supply_hours=4.0
        )
        self.assertEqual(wtr_ind.coverage_gap, 30.0)
        self.assertEqual(wtr_ind.source_gap, 50.0)
        self.assertEqual(wtr_ind.supply_gap, 50.0)

    def test_road_indicator_properties(self):
        dept_pwd, _ = Department.objects.get_or_create(name="Public Works Department", defaults={"code": "PWD"})
        dept_pwd.code = "PWD"
        dept_pwd.save()
        subdiv = self.district.subdivisions.first() if hasattr(self.district, "subdivisions") else None
        if not subdiv:
            from myapp.models import SubDivision
            subdiv = SubDivision.objects.create(district=self.district, name="Test SubDivision")
        block = Block.objects.create(subdivision=subdiv, name="Test PWD Block")
        road = RoadIndicator.objects.create(
            road_name="Test Highway Link", department=dept_pwd, district=self.district, block=block,
            road_length_km=20.0, paved_length_km=15.0, unpaved_poor_length_km=5.0, accessibility_status="MODERATE", bridge_gap_count=1
        )
        self.assertEqual(road.paved_percentage, 75.0)
        self.assertEqual(road.poor_road_percentage, 25.0)
        self.assertEqual(road.accessibility_score, 35.0)

    def test_department_facility_mismatch_validation(self):
        dept_health, _ = Department.objects.get_or_create(name="Health Department", defaults={"code": "HEALTH"})
        dept_health.code = "HEALTH"
        dept_health.save()
        dept_edu, _ = Department.objects.get_or_create(name="Education Department", defaults={"code": "EDUCATION"})
        dept_edu.code = "EDUCATION"
        dept_edu.save()
        fac_health = Facility.objects.create(name="Primary Health Centre Mismatch Test", department=dept_health, district=self.district)

        # Mismatch: Education Department Indicator assigned to Health Facility
        payload = {
            "department": dept_edu.id,
            "district": self.district.id,
            "facility": fac_health.id,
            "indicator_code": "TEACHER_VACANCY",
            "indicator_name": "Teacher Vacancy",
            "value": 5.0
        }
        res = self.client.post("/api/ddst/indicators/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("facility", str(res.data).lower())

    def test_health_sector_crud_endpoints(self):
        dept_health, _ = Department.objects.get_or_create(name="Health Department", defaults={"code": "HEALTH"})
        fac = Facility.objects.create(name="Test Health Facility for CRUD", department=dept_health, district=self.district)

        # 1. Staffing APIView CRUD (POST, GET, PUT, DELETE)
        res_staff = self.client.post("/api/health/staffing/", {
            "facility": fac.id, "cadre": "DOCTOR", "sanctioned_count": 10, "available_count": 6
        }, format="json")
        self.assertEqual(res_staff.status_code, status.HTTP_201_CREATED)
        staff_id = res_staff.data["data"]["id"]

        res_staff_get = self.client.get(f"/api/health/staffing/?id={staff_id}")
        self.assertEqual(res_staff_get.status_code, status.HTTP_200_OK)

        res_staff_put = self.client.put("/api/health/staffing/", {
            "id": staff_id, "available_count": 8
        }, format="json")
        self.assertEqual(res_staff_put.status_code, status.HTTP_200_OK)

        # 2. Workload APIView CRUD
        res_work = self.client.post("/api/health/workload/", {
            "facility": fac.id, "period": "2026-08", "patient_visits": 350, "admissions": 40
        }, format="json")
        self.assertEqual(res_work.status_code, status.HTTP_201_CREATED)

        # 3. Infrastructure APIView CRUD
        res_infra = self.client.post("/api/health/infrastructure/", {
            "facility": fac.id, "period": "2026-08", "bed_count": 30, "icu_bed_count": 4,
            "oxygen_status": "AVAILABLE", "toilet_status": "ADEQUATE", "ramp_status": "FUNCTIONAL"
        }, format="json")
        self.assertEqual(res_infra.status_code, status.HTTP_201_CREATED)

        # 4. Medicine Stock APIView CRUD
        res_med = self.client.post("/api/health/medicines/", {
            "facility": fac.id, "medicine_name": "Paracetamol 500mg", "stock_type": "CRITICAL", "quantity": 1500, "minimum_quantity": 500, "stock_status": "ADEQUATE"
        }, format="json")
        self.assertEqual(res_med.status_code, status.HTTP_201_CREATED)

        # 5. Ambulance APIView CRUD
        res_amb = self.client.post("/api/health/ambulances/", {
            "facility": fac.id, "ambulance_code": "AMB-TEST-001", "status": "AVAILABLE"
        }, format="json")
        self.assertEqual(res_amb.status_code, status.HTTP_201_CREATED)

        # 6. Vaccination Metric APIView CRUD
        subdiv = self.district.subdivisions.first() if hasattr(self.district, "subdivisions") else None
        if not subdiv:
            from myapp.models import SubDivision
            subdiv = SubDivision.objects.create(district=self.district, name="Test SubDiv Vac")
        block = Block.objects.create(subdivision=subdiv, name="Test Block Vac")
        res_vac = self.client.post("/api/health/vaccination/", {
            "block": block.id, "period": "2026-Q3", "target_population": 2000, "vaccinated_count": 1700
        }, format="json")
        self.assertEqual(res_vac.status_code, status.HTTP_201_CREATED)

        # Delete test cleanup
        res_staff_del = self.client.delete(f"/api/health/staffing/?id={staff_id}")
        self.assertEqual(res_staff_del.status_code, status.HTTP_200_OK)






