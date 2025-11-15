from django.core.cache import cache
from rest_framework import status
from . import phone_service, email_service
from .OTP import TOTP
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


class OTPService:

    @staticmethod
    def send_otp_activate_account(email):
        send_otp_key = f'send_otp_{email}_activate_account'
        user = User.objects.filter(email=email).first()

        if not user:
            return {'status': 'Invalid User'}, status.HTTP_400_BAD_REQUEST

        if user.is_active:
            return {'status': 'User Already Activated'}, status.HTTP_400_BAD_REQUEST

        else:
            if cache.get(send_otp_key):
                return {'status': 'Code already has been sented'}, status.HTTP_400_BAD_REQUEST

            cache.set(send_otp_key, True, settings.TOTP_INTERVAL)

            code = TOTP.create(user)
            email_service.email_otp(user, code, activate_account=True)
            return {'status': 'Veryfication Code has been sent to user email'}, status.HTTP_200_OK

    @staticmethod
    def verify_otp_activate_account(email, code):
        send_otp_key = f'send_otp_{email}_activate_account'
        verify_attempt_key = f'verify_attempt_otp_{email}_activate_account'

        attempt = cache.get(verify_attempt_key)
        if attempt:
            if attempt == 1:
                return {'status': 'Too many attempts'}, status.HTTP_400_BAD_REQUEST

        user = User.objects.filter(email=email).first()
        if not user:
            return {'status': 'Invalid User'}, status.HTTP_400_BAD_REQUEST

        if cache.get(send_otp_key):
            if TOTP.verify(user, code):
                user.is_active = True
                user.save()
                cache.delete(send_otp_key)
                return {'status': 'User has been Verified Successfully.'}, status.HTTP_200_OK
            else:
                if attempt:
                    cache.set(verify_attempt_key, attempt - 1, 3600)
                else:
                    cache.set(verify_attempt_key, 4, 3600)

                return {'status': 'Invalid Code'}, status.HTTP_400_BAD_REQUEST
        else:
            return {'status': 'Invalid Code'}, status.HTTP_400_BAD_REQUEST

    @staticmethod
    def send_otp_reset_password(email):
        send_otp_key = f'send_otp_{email}_reset_password'
        if cache.get(send_otp_key):
            return {'status': 'Code already has been sented'}, status.HTTP_400_BAD_REQUEST

        user = User.objects.filter(email=email).first()
        if not user:
            return {'status': 'Invalid User'}, status.HTTP_400_BAD_REQUEST
        if user.is_active:
            cache.set(send_otp_key, True, settings.TOTP_INTERVAL)

            code = TOTP.create(user)
            email_service.email_otp(
                user, code, reset_password=True)
            return {'status': 'Veryfication Code has been sent to user email'}, status.HTTP_200_OK

        else:
            return {'status': 'User is not active'}, status.HTTP_400_BAD_REQUEST

    @staticmethod
    def verify_otp_reset_password(email, code, password):
        send_otp_key = f'send_otp_{email}_reset_password'
        verify_attempt_key = f'verify_attempt_otp_{email}_reset_password'

        attempt = cache.get(verify_attempt_key)
        if attempt:
            if attempt == 1:
                return {'status': 'Too many attempts'}, status.HTTP_400_BAD_REQUEST

        user = User.objects.filter(email=email).first()
        if not user:
            return {'status': 'Invalid User'}, status.HTTP_400_BAD_REQUEST

        if cache.get(send_otp_key):
            if TOTP.verify(user, code):
                user.set_password(password)
                user.save()
                cache.delete(send_otp_key)
                return {'status': 'Password has been reset'}, status.HTTP_200_OK
            else:
                if attempt:
                    cache.set(verify_attempt_key, attempt - 1, 3600)
                else:
                    cache.set(verify_attempt_key, 4, 3600)

                return {'status': 'Invalid Code'}, status.HTTP_400_BAD_REQUEST
        else:
            return {'status': 'Invalid Code'}, status.HTTP_400_BAD_REQUEST

    @staticmethod
    def send_otp_phone_set(user, phone):
        send_otp_key = f'send_otp_{user.id}_phone_set'

        if cache.get(send_otp_key):
            return {'status': 'Code already has been sented'}, status.HTTP_400_BAD_REQUEST

        if user.is_active:
            phone = user.phone
            if not phone:
                cache.set(send_otp_key, True, settings.TOTP_INTERVAL)

                code = TOTP.create(user)
                phone_service.send_verification_code(phone, code)
                return {'status': 'Veryfication Code has been sent to user email'}, status.HTTP_200_OK
            else:
                return {'status': 'User Phone Number Cannot be changed'}, status.HTTP_400_BAD_REQUEST
        else:
            return {'status': 'User Must be active first'}, status.HTTP_400_BAD_REQUEST

    @staticmethod
    def verify_otp_phone_set(user, phone, code):
        send_otp_key = f'send_otp_{user.id}_phone_set'
        verify_attempt_key = f'verify_attempt_otp_{user.id}_phone_set'

        attempt = cache.get(verify_attempt_key)
        if attempt:
            if attempt == 1:
                return {'status': 'Too many attempts'}, status.HTTP_400_BAD_REQUEST

        if cache.get(send_otp_key):
            if TOTP.verify(user, code):
                user.phone = phone
                user.save()
                cache.delete(send_otp_key)
                return {'status': 'Phone has been changed'}, status.HTTP_200_OK
            else:
                if attempt:
                    cache.set(verify_attempt_key, attempt - 1, 3600)
                else:
                    cache.set(verify_attempt_key, 4, 3600)

                return {'status': 'Invalid Code'}, status.HTTP_400_BAD_REQUEST
        else:
            return {'status': 'Invalid Code'}, status.HTTP_400_BAD_REQUEST
