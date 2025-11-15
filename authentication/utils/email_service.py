from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from authentication.tasks import send_email


def email_otp(user, code, activate_account=False, reset_password=False):
    if activate_account:
        subject = 'Verify Your Email'
        template = 'email/activate_account.html'
        message_body = "We received a request to verify your email address for your account.\nPlease use the code below to complete the verification process.\n"

    elif reset_password:
        subject = 'Reset Your Password'
        template = 'email/reset_password.html'
        message_body = "We received a request to reset the password for your account.\nPlease use the code below to securely reset your password.\n"

    if user.first_name and user.last_name:
        if user.gender == 'M':
            user_name = f'Mr. {user.first_name} {user.last_name}'
        else:
            user_name = f'Ms. {user.first_name} {user.last_name}'
    else:
        user_name = f'{user.email}'

    body = render_to_string(
        template, {'code': code, 'user': user_name, 'message_body': message_body})

    from_email = settings.EMAIL_HOST_USER

    to = [user.email]

    send_email.delay(subject, body, from_email, to)
