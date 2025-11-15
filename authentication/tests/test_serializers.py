from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from authentication.serializers import (
    CustomTokenObtainPairSerializer,
    UsersSerializer,
    UserSerializer,
    LogoutSerializers,
    SendOTPActivateAccountSerializer,
    VerifyOTPActivateAccountSerializer,
    SendOTPPasswordResetSerializer,
    VerifyOTPPasswordResetSerializer,
    SendOTPPhoneSetSerializer,
    VerifyOTPPhoneSetSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class CustomTokenObtainPairSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            email="token@example.com", password="Testpass123!"
        )

    def test_validate_includes_email(self):
        serializer = CustomTokenObtainPairSerializer(
            data={"email": "token@example.com", "password": "Testpass123!"}
        )
        self.assertTrue(serializer.is_valid())
        data = serializer.validated_data
        self.assertIn("email", data)
        self.assertEqual(data["email"], self.user.email)


class UsersSerializerTests(TestCase):
    def test_create_user_with_hashed_password_and_inactive(self):
        serializer = UsersSerializer(
            data={"email": "new@example.com", "password": "Testpass123!"}
        )
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertNotEqual(user.password, "Testpass123!")  # hashed
        self.assertFalse(user.is_active)

    def test_password_validation_with_custom_validator(self):
        serializer = UsersSerializer(
            data={"email": "weak@example.com", "password": "123"}
        )
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)


class UserSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="readonly@example.com", password="Testpass123!"
        )

    def test_read_only_fields(self):
        serializer = UserSerializer(instance=self.user)
        data = serializer.data
        self.assertIn("email", data)
        self.assertIn("phone", data)
        self.assertIn("is_active", data)


class LogoutSerializersTests(TestCase):
    def test_accepts_refresh_token(self):
        token = RefreshToken.for_user(
            User.objects.create_user(
                email="logout@example.com", password="Testpass123!")
        )
        serializer = LogoutSerializers(data={"refresh": str(token)})
        self.assertTrue(serializer.is_valid())


class SendOTPActivateAccountSerializerTests(TestCase):
    def test_normalizes_email(self):
        serializer = SendOTPActivateAccountSerializer(
            data={"email": "Test.Email@Gmail.Com"}
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(
            serializer.validated_data["email"], "testemail@gmail.com"
        )


class VerifyOTPActivateAccountSerializerTests(TestCase):
    def test_valid_code(self):
        serializer = VerifyOTPActivateAccountSerializer(
            data={"email": "otp@example.com", "code": 123456}
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["code"], "123456")

    def test_invalid_code_length(self):
        serializer = VerifyOTPActivateAccountSerializer(
            data={"email": "otp@example.com", "code": 12}
        )
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)


class SendOTPPasswordResetSerializerTests(TestCase):
    def test_normalizes_email(self):
        serializer = SendOTPPasswordResetSerializer(
            data={"email": "Upper.Case@Gmail.com"}
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(
            serializer.validated_data["email"], "uppercase@gmail.com"
        )


class VerifyOTPPasswordResetSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="reset@example.com", password="Testpass123!"
        )

    def test_passwords_must_match(self):
        serializer = VerifyOTPPasswordResetSerializer(
            data={
                "email": "reset@example.com",
                "code": 123456,
                "password": "Newpass123!",
                "confirm_password": "Wrongpass123!",
            },
            context={"user": self.user},
        )
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_password_strength_is_checked(self):
        serializer = VerifyOTPPasswordResetSerializer(
            data={
                "email": "reset@example.com",
                "code": 123456,
                "password": "weak",
                "confirm_password": "weak",
            },
            context={"user": self.user},
        )
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)


class SendOTPPhoneSetSerializerTests(TestCase):
    def test_validates_phone_format(self):
        serializer = SendOTPPhoneSetSerializer(data={"phone": "+989121234567"})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["phone"], "09121234567")


class VerifyOTPPhoneSetSerializerTests(TestCase):
    def test_valid_data(self):
        serializer = VerifyOTPPhoneSetSerializer(
            data={"email": "phone@example.com",
                  "phone": "09121234567", "code": 123456}
        )
        self.assertTrue(serializer.is_valid())

    def test_invalid_phone_format(self):
        serializer = VerifyOTPPhoneSetSerializer(
            data={"email": "phone@example.com",
                  "phone": "912123456", "code": 123456}
        )
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_invalid_email_format(self):
        serializer = VerifyOTPPhoneSetSerializer(
            data={"email": "invalid@em.ail.com",
                  "phone": "09121234567", "code": 123456}
        )
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_invalid_code_length(self):
        serializer = VerifyOTPPhoneSetSerializer(
            data={"email": "phone@example.com",
                  "phone": "09121234567", "code": 12}
        )
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)
