from django.dispatch import Signal, receiver
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from .models import Cart

User = get_user_model()


@receiver(post_save, sender=User)
def create_cart(sender, instance, created, **kwargs):
    if created:
        Cart.objects.create(user=instance)
