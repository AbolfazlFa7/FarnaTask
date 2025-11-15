from django.test import TestCase
from django.contrib.auth import get_user_model
from product.models import Cart

User = get_user_model()


class SignalsTests(TestCase):
    def test_post_save_creates_cart_for_new_user(self):
        user = User.objects.create_user(
            email="signals@example.com", password="Testpass123!")
        cart_exists = Cart.objects.filter(user=user).exists()
        self.assertTrue(cart_exists)
        cart = Cart.objects.get(user=user)
        self.assertEqual(cart.user, user)
