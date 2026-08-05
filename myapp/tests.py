from django.test import TestCase, Client
from rest_framework.test import APIClient
from rest_framework import status
from myapp.models import State, District, Department, User, Facility


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
