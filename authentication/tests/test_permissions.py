from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from authentication.permissions import IsOwnerOrAdmin, IsAnonymous

User = get_user_model()


class IsOwnerOrAdminTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.owner = User.objects.create_user(
            email="owner@example.com", password="Testpass123!"
        )
        self.other = User.objects.create_user(
            email="other@example.com", password="Testpass123!"
        )
        self.admin = User.objects.create_superuser(
            email="admin@example.com", password="Adminpass123!"
        )
        self.permission = IsOwnerOrAdmin()

    def test_allows_access_for_owner(self):
        request = self.factory.get("/")
        request.user = self.owner
        self.assertTrue(self.permission.has_object_permission(
            request, None, self.owner))

    def test_allows_access_for_admin(self):
        request = self.factory.get("/")
        request.user = self.admin
        self.assertTrue(self.permission.has_object_permission(
            request, None, self.owner))

    def test_denies_access_for_non_owner_non_admin(self):
        request = self.factory.get("/")
        request.user = self.other
        self.assertFalse(self.permission.has_object_permission(
            request, None, self.owner))


class IsAnonymousTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsAnonymous()
        self.user = User.objects.create_user(
            email="anon@example.com", password="Testpass123!"
        )

    def test_allows_for_anonymous_users(self):
        request = self.factory.get("/")
        request.user = type("Anonymous", (), {"is_anonymous": True})()
        self.assertTrue(self.permission.has_permission(request, None))

    def test_denies_for_authenticated_users(self):
        request = self.factory.get("/")
        request.user = self.user
        self.assertFalse(self.permission.has_permission(request, None))
