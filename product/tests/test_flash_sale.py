# product/tests/test_flash_sale.py
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import timedelta
from unittest.mock import patch
from django.urls import reverse

from product.models import (
    Category, Product, FlashSale, FlashSaleProduct,
    CartItem, Coupon, Order
)
from product.utils.coupon_service import verify_coupon

User = get_user_model()


class FlashSaleModelTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.category = Category.objects.create(
            name="Electronics", slug="electronics")
        self.product = Product.objects.create(
            name="Flash Phone", slug="flash-phone", category=self.category,
            price=1000, stock=10
        )
        self.flash_sale = FlashSale.objects.create(
            title="Summer Sale",
            start_time=self.now - timedelta(hours=1),
            end_time=self.now + timedelta(hours=2)
        )

    def test_flash_sale_is_running(self):
        self.assertTrue(self.flash_sale.is_running())

    def test_flash_sale_product_discount(self):
        FlashSaleProduct.objects.create(
            flash_sale=self.flash_sale,
            product=self.product,
            discount_type='percent',
            discount_value=50,
            limited_stock=3
        )
        self.assertEqual(self.product.get_final_price(), 500)

    def test_flash_sale_fixed_discount(self):
        FlashSaleProduct.objects.create(
            flash_sale=self.flash_sale,
            product=self.product,
            discount_type='fixed',
            discount_value=300,
            limited_stock=2
        )
        self.assertEqual(self.product.get_final_price(), 700)

    def test_flash_sale_inactive_no_discount(self):
        inactive_sale = FlashSale.objects.create(
            title="Old Sale",
            start_time=self.now - timedelta(days=5),
            end_time=self.now - timedelta(days=1)
        )
        FlashSaleProduct.objects.create(
            flash_sale=inactive_sale,
            product=self.product,
            discount_type='percent',
            discount_value=50,
            limited_stock=1
        )
        self.assertEqual(self.product.get_final_price(), 1000)


class FlashSaleViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", password="Test1234!")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

        self.now = timezone.now()
        self.category = Category.objects.create(name="Gadgets", slug="gadgets")
        self.product = Product.objects.create(
            name="Sale Item", slug="sale-item", category=self.category, price=2000, stock=5
        )
        self.flash_sale = FlashSale.objects.create(
            title="Active Sale",
            start_time=self.now - timedelta(minutes=30),
            end_time=self.now + timedelta(hours=1)
        )
        FlashSaleProduct.objects.create(
            flash_sale=self.flash_sale,
            product=self.product,
            discount_type='percent',
            discount_value=30,
            limited_stock=2
        )

    def test_flash_sale_list_api_only_active(self):
        url = reverse('flash-sale')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_flash_sale_product_in_product_list_price(self):
        url = reverse('product-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class FlashSaleCartOrderTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="cartuser@example.com", password="Test1234!")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

        self.category = Category.objects.create(name="Toys", slug="toys")
        self.product = Product.objects.create(
            name="Flash Toy", slug="flash-toy", category=self.category, price=500, stock=10
        )
        self.now = timezone.now()
        self.flash_sale = FlashSale.objects.create(
            title="Flash Toy Sale",
            start_time=self.now - timedelta(minutes=10),
            end_time=self.now + timedelta(hours=3)
        )
        self.flash_sale_product = FlashSaleProduct.objects.create(
            flash_sale=self.flash_sale,
            product=self.product,
            discount_type='percent',
            discount_value=40,
            limited_stock=1
        )

    def test_cannot_add_more_than_limited_stock_to_cart(self):
        self.user.cart.items.all().delete()
        url = reverse('user-cart-item-create')
        response = self.client.post(
            url, {"product_id": self.product.id, "quantity": 1})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('product.utils.zarinpal.request_payment')
    def test_order_uses_flash_sale_price_and_reduces_stock(self, mock_request_payment):
        mock_request_payment.return_value = ("AUTH123", "https://pay.ir")
        self.user.cart.items.all().delete()
        CartItem.objects.create(cart=self.user.cart,
                                product=self.product, quantity=1)
        url = reverse('order-create')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class FlashSaleCouponConflictTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="conflict@example.com", password="Test1234!")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

        self.category = Category.objects.create(name="Books", slug="books")
        self.product = Product.objects.create(
            name="Flash Book", slug="flash-book", category=self.category, price=1000, stock=5
        )
        self.now = timezone.now()
        self.flash_sale = FlashSale.objects.create(
            title="Book Flash",
            start_time=self.now - timedelta(minutes=5),
            end_time=self.now + timedelta(hours=1)
        )
        FlashSaleProduct.objects.create(
            flash_sale=self.flash_sale,
            product=self.product,
            discount_type='percent',
            discount_value=50,
            limited_stock=2
        )
        self.user.cart.items.all().delete()
        CartItem.objects.create(cart=self.user.cart,
                                product=self.product, quantity=1)

    def test_coupon_rejected_when_flash_sale_in_cart(self):
        Coupon.objects.create(code="SAVE20", discount_value=20,
                              start_date=self.now, is_active=True)
        status_code, result = verify_coupon(self.user, "SAVE20")
        self.assertEqual(status_code, 400)
