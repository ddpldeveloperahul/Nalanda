from django.test import TestCase, Client
from rest_framework.test import APIClient
from rest_framework import status
from myapp.models import State, District, Department, User, Facility, Role


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

