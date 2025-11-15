from django.test import TestCase
from django.core.exceptions import ValidationError
from authentication.utils.validators import (
    CustomPasswordValidator,
    normalize_email,
    normalize_phone,
)


class CustomPasswordValidatorTests(TestCase):
    def setUp(self):
        self.validator = CustomPasswordValidator()

    def test_rejects_password_too_short(self):
        with self.assertRaises(ValidationError):
            self.validator.validate("Ab1!")

    def test_rejects_password_too_long(self):
        with self.assertRaises(ValidationError):
            self.validator.validate("A" * 25 + "1!")

    def test_requires_uppercase_lowercase_digit_and_punctuation(self):
        with self.assertRaises(ValidationError):
            self.validator.validate("nouppercase!3")

        with self.assertRaises(ValidationError):
            self.validator.validate("NOLOWERCASE!3")

        with self.assertRaises(ValidationError):
            self.validator.validate("NoDigits!")

        with self.assertRaises(ValidationError):
            self.validator.validate("NoPunctuation1")

    def test_accepts_strong_password(self):
        self.validator.validate("ValidPass1!")


class NormalizeEmailTests(TestCase):
    def test_lowers_domain(self):
        email = "User@Example.COM"
        self.assertEqual(normalize_email(email), "user@example.com")

    def test_removes_gmail_dots(self):
        email = "Te.st.Email@Gmail.Com"
        self.assertEqual(normalize_email(email), "testemail@gmail.com")

    def test_rejects_invalid_email_format(self):
        with self.assertRaises(ValidationError):
            normalize_email("invalid-email")
        with self.assertRaises(ValidationError):
            normalize_email("invalid@email")
        with self.assertRaises(ValidationError):
            normalize_email("invalid@ema.il.com")


class ValidatePhoneTests(TestCase):
    def test_normalizes_plus98_to_zero_prefix(self):
        phone = "+989121234567"
        normalized = normalize_phone(phone)
        self.assertEqual(normalized, "09121234567")

    def test_accepts_valid_iranian_number(self):
        phone = "09121234567"
        normalized = normalize_phone(phone)
        self.assertEqual(normalized, "09121234567")

    def test_rejects_non_iranian_number(self):
        with self.assertRaises(ValidationError):
            normalize_phone("+12025550123")

    def test_rejects_invalid_format(self):
        with self.assertRaises(ValidationError):
            normalize_phone("912123456")
