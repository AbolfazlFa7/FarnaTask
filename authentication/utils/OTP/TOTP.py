from django.conf import settings
from pyotp import TOTP
import hashlib
import base64


def create(user) -> int:
    secret = user.secret_key
    hashed = hashlib.sha256(secret.encode()).digest()
    base32 = base64.b32encode(hashed).decode()
    totp = TOTP(base32, digits=settings.TOTP_DIGITS,
                interval=settings.TOTP_INTERVAL)
    return totp.now()


def verify(user, code) -> bool:
    secret = user.secret_key
    hashed = hashlib.sha256(secret.encode()).digest()
    base32 = base64.b32encode(hashed).decode()
    totp = TOTP(base32, digits=settings.TOTP_DIGITS,
                interval=settings.TOTP_INTERVAL)
    return totp.verify(code)
