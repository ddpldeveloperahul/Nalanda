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
