from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from unittest.mock import patch
from django.db import reset_queries, connection
from django.utils import timezone
from product.models import (
    Category,
    Product,
    Coupon,
    Review,
    Cart,
    CartItem,
    Order,
    Payment,
)

User = get_user_model()
connection.force_debug_cursor = True


class CategoryViewTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = User.objects.create_superuser(
            email="admin@example.com", password="Adminpass123!")
        cls.user = User.objects.create_user(
            email="user@example.com", password="Adminpass123!")
        cls.cat = Category.objects.create(
            name="Active", slug="active", is_active=True)
        cls.url = reverse("category-list")

    def test_category_list_lists_only_active(self):
        Category.objects.create(
            name="Inactive", slug="inactive", is_active=False)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        for cat in res.data['results']:
            self.assertEqual(cat['slug'], self.cat.slug)

    def test_category_list(self):
        res1 = self.client.get(self.url)
        res2 = self.client.force_authenticate(self.user)
        res2 = self.client.get(self.url)
        res3 = self.client.force_authenticate(self.admin)
        res3 = self.client.get(self.url)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res3.status_code, 200)

    def test_admin_category_management_crud(self):
        url = reverse("admin-category-list")
        self.client.force_authenticate(self.admin)
        res = self.client.post(url, {"name": "Cat", "slug": "cat"})
        self.assertEqual(res.status_code, 201)
        self.client.force_authenticate(self.user)
        res = self.client.post(url, {"name": "Cat", "slug": "cat"})
        self.assertEqual(res.status_code, 403)


class ProductViewTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cat1 = Category.objects.create(name="Phones", slug="phones")
        cls.cat2 = Category.objects.create(name="Laptops", slug="laptops")
        cls.product1 = Product.objects.create(
            name="iPhone", slug="iphone", category=cls.cat1, price=1000, stock=5)
        cls.product2 = Product.objects.create(
            name="MacBook", slug="macbook", category=cls.cat2, price=2000, stock=10)
        cls.url = reverse("product-list")

    def test_product_list_and_carts_count(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertIn("carts_count", res.data['results'][0])

    def test_product_list_filter(self):
        res = self.client.get(self.url, {"category": self.cat1.name})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['results']), 1)

    def test_product_detail_retrieves_with_prefetch(self):
        url = reverse("product-detail", args=[self.product1.slug])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertIn("attributes", res.data)

    def test_product_query_number(self):
        reset_queries()
        url = reverse("product-list")
        self.client.get(url, {"category": self.cat1.name})
        self.assertTrue(len(connection.queries) <= 7)


class CouponViewTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cat = Category.objects.create(name="Books", slug="books")
        cls.product = Product.objects.create(
            name="Book", slug="book", category=cls.cat, price=1000, stock=10)
        cls.coupon = Coupon.objects.create(
            code="OFF10", discount_value=10, start_date=timezone.now(), max_usage=5, is_active=True)
        cls.user = User.objects.create_user(
            email="user@example.com", password="Testpass123!")

    def test_coupon_verify_copoun_validates(self):
        CartItem.objects.create(cart=self.user.cart,
                                product=self.product, quantity=2)
        self.client.force_authenticate(self.user)
        url = reverse("coupon-verify")
        res = self.client.post(url, {"code": "OFF10"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['final_amount'], 1800)


class ReviewViewTests(APITestCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.user = User.objects.create_user(
            email="rev@example.com", password="Testpass123!")
        self.cat = Category.objects.create(name="Laptops", slug="laptops")
        self.product = Product.objects.create(
            name="MacBook", slug="macbook", category=self.cat, price=2000)

    def test_review_create_for_authenticated_user(self):
        self.client.force_authenticate(self.user)
        url = reverse("review-create")
        res = self.client.post(
            url, {"product": self.product.id, "rating": 5, "title": "Excellent", "comment": "very good"})
        self.assertEqual(res.status_code, 201)

    def test_review_update_for_owner(self):
        self.client.force_authenticate(self.user)
        review = Review.objects.create(
            user=self.user, product=self.product, rating=4, comment="Good")
        url = reverse("review-update", args=[review.id])
        res = self.client.patch(url, {"rating": 3})
        self.assertEqual(res.status_code, 200)


class CartViewTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            email="cart@example.com", password="Testpass123!")
        cls.cat = Category.objects.create(name="Gadgets", slug="gadgets")
        cls.product = Product.objects.create(
            name="Camera", slug="camera", category=cls.cat, price=500, stock=3)

    def setUp(self):
        self.client.force_authenticate(self.user)

    def test_user_cart_list_with_prefetch(self):
        url = reverse("user-cart-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

    def test_user_cart_item_create_adds_item(self):
        url = reverse("user-cart-item-create")
        res = self.client.post(
            url, {"product_id": self.product.id, "quantity": 1})
        self.assertEqual(res.status_code, 201)

    def test_user_cart_item_detail_crud(self):
        product = Product.objects.create(
            name="Phone", slug="phone", category=self.cat, price=500, stock=3)
        item = CartItem.objects.create(
            cart=self.user.cart, product=product, quantity=1)
        url = reverse("cart-item-detail", args=[item.id])
        res = self.client.patch(url, {"quantity": 2})
        self.assertEqual(res.status_code, 200)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, 204)


class OrderPaymentViewTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            email="order@example.com", password="Testpass123!")
        cls.cat = Category.objects.create(
            name="Accessories", slug="accessories")
        cls.product = Product.objects.create(
            name="Headphones", slug="headphones", category=cls.cat, price=100)
        cls.item = CartItem.objects.create(
            cart=cls.user.cart, product=cls.product, quantity=2)

    def setUp(self):
        self.client.force_authenticate(self.user)

    @patch('product.views.request_payment')
    @patch('product.views.verify_payment')
    def test_create_order_and_verify_payment(self, mock_verify_payment, mock_request_payment, ):
        mock_request_payment.return_value = (
            "AUTHORITY", "https://example.com")
        mock_verify_payment.return_value = ("REF_ID", "success")

        url = reverse("order-create")
        res = self.client.post(url)
        self.assertEqual(res.status_code, 201)
        url = reverse("payment-verify")
        res = self.client.get(url, {"Authority": 'AUTHORITY', "Status": "OK"})
        self.assertEqual(res.status_code, 200)

    def test_order_list_and_detail(self):
        order = Order.objects.create(
            user=self.user, total_amount=100, final_amount=100)
        url_list = reverse("order-list")
        url_detail = reverse("order-detail", args=[order.id])
        res1 = self.client.get(url_list)
        res2 = self.client.get(url_detail)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res2.status_code, 200)

    def test_payment_list(self):
        order = Order.objects.create(
            user=self.user, total_amount=50, final_amount=50)
        Payment.objects.create(order=order, amount=50, status="pending")
        url = reverse("payment-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
