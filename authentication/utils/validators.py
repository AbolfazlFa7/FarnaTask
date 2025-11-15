from django.utils.translation import gettext as _
from string import ascii_lowercase, ascii_uppercase, punctuation, digits
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
import re


class CustomPasswordValidator:
    def validate(self, password, user=None):
        """
        Validates that the password meets the following criteria:
        - At least 8 characters, max 20
        - Must contain at least one of each:
            - UpperCase letter
            - LowerCase letter
            - Digit
            - Punctuation mark

        Example:
            A12345a@ -> valid
            A12345a  -> invalid
        """
        if not (8 <= len(password) <= 20):
            raise ValidationError(
                "Password must be between 8 and 20 characters.",
                code='password_length_invalid'
            )

        password_set = set(password)
        if not all([
            bool(set(ascii_lowercase) & password_set),
            bool(set(ascii_uppercase) & password_set),
            bool(set(punctuation) & password_set),
            bool(set(digits) & password_set),
        ]):
            raise ValidationError(
                "Password must contain at least one UpperCase letter, LowerCase letter, Digit, and Punctuation mark.",
                code='Weak_Password'
            )

    def get_error_message(self):
        return "This password is not strong enough. it must be 8-20 characters and include at least one UpperCase letter, LowerCase letter, Digit, and Punctuation mark."

    def get_help_text(self):
        return "Your password must be 8-20 characters and include at least one UpperCase letter, LowerCase letter, Digit, and Punctuation mark."


def normalize_email(email: str):
    """
    - strip whitespaces
    - lower case the domin part of the email
    - detact the Gmail Dot Trick, and fix it

    example:
            'Abc.def@email.com' --> 'Abcdef@email.com' 
            'Abcdef@ema.il.com' --> raise ValueError
    """

    email = email.lower().strip()
    dj_email_validator = EmailValidator()
    dj_email_validator(email)
    reversed_email = email[::-1]
    suffix, prefix = re.findall(r'(.*?\..*?@)(.*)', reversed_email)[0]
    prefix = prefix.replace('.', '')
    normalized_email = prefix[::-1] + suffix[::-1]

    if normalized_email.count('.') > 1:
        raise ValidationError('Your email is not in the correct format')

    return normalized_email


def normalize_phone(phone: str):
    """
    - Validate phone number format for Iran
    - Normalize to format starting with '0'

    Example:
    '+989123456789' --> '09123456789'
    '09123456789' --> '09123456789'
    Invalid format raises ValidationError
    """

    match = re.findall(r'^(\+98|0)?(9\d{9})$', phone)
    if match:
        return '0' + match[0][1]
    raise ValidationError('Invalid Phone Number')
