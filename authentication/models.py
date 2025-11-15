from django.db import models
from django.contrib.auth.models import AbstractUser
from .utils.validators import normalize_email, normalize_phone
from django.utils.translation import gettext_lazy as _
from .manager import UserManager


class User(AbstractUser):
    username = None
    birthday = models.DateField(
        null=True, blank=True, verbose_name=_('Birthday'))
    gender = models.CharField(max_length=1, choices=(
        ('M', _('Male')), ('F', _('Female'))), default='M', verbose_name=_('Gender'))
    phone = models.CharField(
        max_length=13, null=True, blank=True, unique=True, verbose_name=_('Phone'))
    email = models.EmailField(unique=True, verbose_name=_('Email'))
    is_active = models.BooleanField(default=False, verbose_name=_('Is Active'))
    objects = UserManager()
    secret_key = models.CharField(
        max_length=32, null=False, blank=False, verbose_name=_('Secret Key'))

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    def clean(self):
        if self.phone:
            self.phone = normalize_phone(self.phone)
        if self.email:
            self.email = normalize_email(self.email)
        return super().clean()
