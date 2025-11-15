from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class UserModelTests(TestCase):
    def setUp(self):
        self.invalid_password = "Testpass"

    def test_create_superuser_with_invalid_password(self):
        user = User.objects.create_superuser(
            email="super@example.com", password=self.invalid_password)
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
