from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class AuthViewsTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            email="user@example.com", password="Testpass123!"
        )
        cls.admin = User.objects.create_superuser(
            email="admin@example.com", password="Adminpass123!"
        )

    def test_token_obtain_pair_returns_tokens_and_email_inactive_user(self):
        url = reverse("Token")
        response = self.client.post(
            url, {"email": "user@example.com", "password": "Testpass123!"}
        )
        self.assertEqual(response.status_code, 401)

    def test_token_obtain_pair_returns_tokens_and_email_active_user(self):
        self.user.is_active = True
        self.user.save()
        url = reverse("Token")
        response = self.client.post(
            url, {"email": "user@example.com", "password": "Testpass123!"}
        )
        self.assertTrue(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["email"], self.user.email)

    def test_users_api_view_get_lists_users_for_admin(self):
        url = reverse("users")
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_users_api_view_post_creates_user_for_anonymous(self):
        url = reverse("users")
        response = self.client.post(
            url, {"email": "newuser@example.com", "password": "Testpass123!"}
        )
        self.assertEqual(response.status_code, 201)

    def test_user_api_view_get_for_owner(self):
        url = reverse("user", args=[self.user.id])
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], self.user.email)

    def test_user_api_view_get_for_another_user(self):
        self.another_user = User.objects.create_user(
            email="anotheruser@example.com", password="Testpass123!"
        )
        url = reverse("user", args=[self.user.id])
        self.client.force_authenticate(user=self.another_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_user_api_view_get_for_anonymous(self):
        url = reverse("user", args=[self.user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

    def test_user_api_view_get_for_admin(self):
        url = reverse("user", args=[self.user.id])
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_user_api_view_patch_updates_first_name(self):
        url = reverse("user", args=[self.user.id])
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(url, {"first_name": "Ali"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["first_name"], "Ali")

    def test_user_api_view_delete_removes_user(self):
        url = reverse("user", args=[self.user.id])
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

    def test_user_me_api_view_retrieves_current_user(self):
        url = reverse("user_me")
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], self.user.email)

    def test_logout_api_view_blacklists_valid_refresh(self):
        url = reverse("logout")
        refresh = str(RefreshToken.for_user(self.user))
        self.client.force_authenticate(user=self.user)
        response = self.client.post(url, {"refresh": refresh})
        self.assertEqual(response.status_code, 200)

    def test_logout_api_view_rejects_invalid_refresh(self):
        url = reverse("logout")
        self.client.force_authenticate(user=self.user)
        response = self.client.post(url, {"refresh": "invalidtoken"})
        self.assertEqual(response.status_code, 400)
