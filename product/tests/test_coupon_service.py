from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from product.models import Category, Product, Coupon, CategoryCoupon, ProductCoupon, Cart, CartItem
from product.utils.coupon_service import verify_coupon


User = get_user_model()


class CouponServiceTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            email="coupon@example.com", password="Testpass123!")
        cls.cat = Category.objects.create(
            name="Electronics", slug="electronics")
        cls.product = Product.objects.create(
            name="Phone", slug="phone", sku="SKU1", category=cls.cat, price=1000, stock=5
        )
        cls.item = CartItem.objects.create(
            cart=cls.user.cart, product=cls.product, quantity=1)

    def test_verify_coupon_checks_existence_and_active(self):
        coupon = Coupon.objects.create(
            code="OFF10", discount_value=10, start_date=timezone.now(), max_usage=5, is_active=True)
        status, result = verify_coupon(self.user, coupon.code)
        self.assertEqual(status, 200)
        self.assertTrue(result["status"] == "Coupon is valid")

        coupon.is_active = False
        coupon.save()
        status, result = verify_coupon(self.user, coupon.code)
        self.assertEqual(status, 400)

    def test_verify_coupon_checks_dates(self):
        valid_coupon = Coupon.objects.create(
            code="TIME10",
            discount_value=10,
            max_usage=5,
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=1),
            is_active=True
        )
        expired_coupon = Coupon.objects.create(
            code="OLD10",
            discount_value=10,
            max_usage=5,
            start_date=timezone.now() - timedelta(days=10),
            end_date=timezone.now() - timedelta(days=5),
            is_active=True
        )
        status, result = verify_coupon(self.user, valid_coupon.code)
        self.assertEqual(status, 200)

        status, result = verify_coupon(self.user, expired_coupon.code)
        self.assertEqual(status, 400)

    def test_verify_coupon_checks_usage_limit(self):
        coupon = Coupon.objects.create(
            code="LIMIT1", discount_value=10, max_usage=1, usage_count=1, start_date=timezone.now(), is_active=True)
        status, result = verify_coupon(self.user, coupon.code)
        self.assertEqual(status, 400)

    def test_verify_coupon_checks_min_order_amount(self):
        coupon = Coupon.objects.create(
            code="MIN5000", discount_value=10, max_usage=5, min_order_amount=5000, start_date=timezone.now(), is_active=True)
        status, result = verify_coupon(self.user, coupon.code)
        self.assertEqual(status, 400)

    def test_verify_coupon_applies_to_products_categories(self):
        coupon = Coupon.objects.create(
            code="PROD10", discount_value=10, start_date=timezone.now(), max_usage=5, is_active=True)
        ProductCoupon.objects.create(product=self.product, coupon=coupon)
        status, result = verify_coupon(self.user, coupon.code)
        self.assertEqual(status, 200)

        coupon2 = Coupon.objects.create(
            code="CAT10", discount_value=10, start_date=timezone.now(), max_usage=5, is_active=True)
        CategoryCoupon.objects.create(category=self.cat, coupon=coupon2)
        status, result = verify_coupon(self.user, coupon2.code)
        self.assertEqual(status, 200)

    def test_verify_coupon_calculates_final_amount_percent(self):
        coupon = Coupon.objects.create(
            code="OFF20", discount_value=20, start_date=timezone.now(), max_usage=5, is_active=True)
        status, result = verify_coupon(self.user, coupon.code)
        self.assertEqual(status, 200)
        self.assertEqual(result["coupon_value"], Decimal("20"))
        self.assertEqual(result["final_amount"], Decimal("800"))

    def test_verify_coupon_calculates_final_amount_fixed(self):
        coupon = Coupon.objects.create(
            code="FIX100", discount_value=100, discount_type='fixed', start_date=timezone.now(), max_usage=5, is_active=True)
        status, result = verify_coupon(self.user, coupon.code)
        self.assertEqual(status, 200)
        self.assertEqual(result["coupon_value"], Decimal("100"))
        self.assertEqual(result["final_amount"], Decimal("900"))
