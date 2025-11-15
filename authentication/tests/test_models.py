from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from authentication.utils.validators import normalize_email

User = get_user_model()


class UserModelTests(TestCase):
    def setUp(self):
        self.valid_password = "Testpass123!"

    def test_create_user_with_valid_data(self):
        user = User.objects.create_user(
            email="test@example.com", password=self.valid_password)
        self.assertEqual(user.email, "test@example.com")
        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.secret_key)

    def test_unique_email_constraint(self):
        User.objects.create_user(
            email="unique@example.com", password=self.valid_password)
        with self.assertRaises(Exception):
            User.objects.create_user(
                email="unique@example.com", password=self.valid_password)

    def test_phone_field_valid_iranian_number(self):
        user_1 = User.objects.create_user(
            email="phone_1@example.com", password=self.valid_password, phone="09121234567")
        user_2 = User.objects.create_user(
            email="phone_2@example.com", password=self.valid_password, phone="+989121234568")
        self.assertEqual(user_1.phone, "09121234567")
        self.assertEqual(user_2.phone, "09121234568")

    def test_phone_field_invalid_format(self):
        with self.assertRaises(ValidationError):
            user = User(email="invalidphone@example.com", phone="9385640365")
            user.full_clean()

    def test_phone_max_length(self):
        with self.assertRaises(ValidationError):
            user = User(email="invalidphone@example.com",
                        phone="93856403654321")
            user.full_clean()

    def test_email_normalization_lowercase_and_email_dot_trick(self):
        email = "Te.st.Email@Gmail.Com"
        normalized = normalize_email(email)
        self.assertEqual(normalized, "testemail@gmail.com")

    def test_email_normalization_bad_format(self):
        email = "test@exa.mple.com"
        with self.assertRaises(ValidationError):
            normalize_email(email)

    def test_secret_key_generated_automatically(self):
        user = User.objects.create_user(
            email="secret@example.com", password=self.valid_password)
        self.assertIsNotNone(user.secret_key)
        self.assertEqual(len(user.secret_key), 32)

    def test_str_returns_email(self):
        user = User.objects.create_user(
            email="str@example.com", password=self.valid_password)
        self.assertEqual(str(user), "str@example.com")

    def test_required_fields_empty(self):
        self.assertEqual(User.REQUIRED_FIELDS, [])
