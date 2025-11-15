from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import UserManager
from pyotp import random_base32


class UserManager(UserManager):
    """
    validate_in_lower_layer: it is for when 
    """

    def create_user(self, email, password, validator_in_lower_layer=True, **extra_fields):
        user = self.model(email=email, **extra_fields)
        user.secret_key = random_base32()
        user.set_password(password)
        if validator_in_lower_layer:
            validate_password(password, user=user)
            user.full_clean()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        user = self.create_user(
            email=email, password=password, validator_in_lower_layer=False, **extra_fields)
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save(using=self._db)
        return user
