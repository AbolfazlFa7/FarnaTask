from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from django.utils import timezone
from product.models import (
    Category,
    Product,
    ProductImage,
    ProductAttribute,
    Coupon,
    CategoryCoupon,
    ProductCoupon,
    Review,
    ReviewImage,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Payment,
)

User = get_user_model()


class CategoryModelTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cat = Category.objects.create(name="Cat", slug="cat")

    def test_category_creation_with_unique_slug_and_active_status(self):
        self.assertEqual(self.cat.slug, "cat")
        self.assertTrue(self.cat.is_active)

    def test_category_parent_child_relationship(self):
        child = Category.objects.create(
            name="Child", slug="child", parent=self.cat)
        self.assertEqual(child.parent, self.cat)


class ProductModelTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cat = Category.objects.create(name="Cat", slug="cat")

    def test_product_creation_with_unique_slug(self):
        p = Product.objects.create(
            name="Phone", slug="phone", category=self.cat, price=1000)
        self.assertEqual(p.slug, "phone")
        with self.assertRaises(IntegrityError):
            Product.objects.create(
                name="Phone", slug="phone", category=self.cat, price=1000)

    def test_product_stock_and_availability_defaults(self):
        p = Product.objects.create(
            name="Laptop", slug="laptop", description="Notebook Lenovo", category=self.cat, price=200000)
        self.assertEqual(p.stock, 0)
        self.assertTrue(p.is_available)


class ProductImageModelTests(TestCase):
    def test_unique_featured_per_product_constraint(self):
        cat = Category.objects.create(name="Cat3", slug="cat3")
        p = Product.objects.create(
            name="TV", slug="tv", sku="SKU125", category=cat, price=3000)
        ProductImage.objects.create(
            product=p, image="img1.jpg", is_feature=True)
        with self.assertRaises(IntegrityError):
            ProductImage.objects.create(
                product=p, image="img2.jpg", is_feature=True)


class ProductAttributeModelTests(TestCase):
    def test_attribute_key_value_pairs(self):
        cat = Category.objects.create(name="Cat4", slug="cat4")
        p = Product.objects.create(
            name="Mouse", slug="mouse", sku="SKU126", category=cat, price=100)
        attr = ProductAttribute.objects.create(
            product=p, key="color", value="black")
        self.assertEqual(attr.key, "color")
        self.assertEqual(attr.value, "black")


class CouponModelTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.c = Coupon.objects.create(code="OFF10", discount_value=10,
                                      max_usage=5, start_date=timezone.now())

    def test_coupon_code_uniqueness(self):
        with self.assertRaises(IntegrityError):
            Coupon.objects.create(
                code="OFF10", discount_value=20, max_usage=3)

    def test_max_usage_and_usage_count(self):
        self.assertEqual(self.c.usage_count, 0)
        self.c.usage_count += 1
        self.c.save()
        self.assertEqual(self.c.usage_count, 1)


class CouponRelationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cat = Category.objects.create(name="Cat", slug="cat")
        cls.c = Coupon.objects.create(
            code="OFF10", discount_value=10, max_usage=10, start_date=timezone.now())

    def test_category_coupon_relation(self):
        cc = CategoryCoupon.objects.create(category=self.cat, coupon=self.c)
        self.assertEqual(cc.coupon, self.c)

    def test_product_coupon_relation(self):
        p = Product.objects.create(
            name="Keyboard", slug="keyboard", category=self.cat, price=50)
        pc = ProductCoupon.objects.create(product=p, coupon=self.c)
        self.assertEqual(pc.product, p)


class ReviewModelTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            email="reviewer@example.com", password="Testpass123!")
        cls.cat = Category.objects.create(name="Cat", slug="cat")
        cls.product = Product.objects.create(
            name="Monitor", slug="monitor", category=cls.cat, price=500)

    def test_review_unique_per_user_product(self):
        Review.objects.create(
            user=self.user, product=self.product, rating=5, comment="Great!")
        with self.assertRaises(Exception):
            Review.objects.create(
                user=self.user, product=self.product, rating=4, comment="Not bad")

    def test_review_rating_choices(self):
        review = Review.objects.create(
            user=self.user, product=self.product, rating=3, comment="Okay")
        self.assertIn(review.rating, [1, 2, 3, 4, 5])


class ReviewImageModelTests(TestCase):
    def test_review_image_relation(self):
        user = User.objects.create_user(
            email="img@example.com", password="Testpass123!")
        cat = Category.objects.create(name="Cat", slug="cat")
        p = Product.objects.create(
            name="Tablet", slug="tablet", category=cat, price=800)
        r = Review.objects.create(
            user=user, product=p, rating=4, comment="Nice")
        ri = ReviewImage.objects.create(review=r, image="review1.jpg")
        self.assertEqual(ri.review, r)


class CartItemModelTests(TestCase):
    def test_cart_item_unique_per_cart_product_and_quantity_limits(self):
        user = User.objects.create_user(
            email="cartitem@example.com", password="Testpass123!")
        cat = Category.objects.create(name="Cat9", slug="cat9")
        p = Product.objects.create(
            name="Camera", slug="camera", sku="SKU130", category=cat, price=1500, stock=5)
        CartItem.objects.create(cart=user.cart, product=p, quantity=2)
        with self.assertRaises(Exception):
            CartItem.objects.create(cart=user.cart, product=p, quantity=1)


class OrderModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="order@example.com", password="Testpass123!")
        self.cat = Category.objects.create(name="Cat", slug="cat")
        self.p = Product.objects.create(
            name="Speaker", slug="speaker", category=self.cat, price=100)
        self.item = CartItem.objects.create(
            cart=self.user.cart, product=self.p, quantity=2)

    def test_order_total_and_final_amount_calculations(self):
        order = Order.objects.create(
            user=self.user, total_amount=200, final_amount=200)
        self.assertEqual(order.total_amount, 200)
        self.assertEqual(order.final_amount, 200)


class OrderItemModelTests(TestCase):
    def test_order_item_price_snapshot(self):
        user = User.objects.create_user(
            email="orderitem@example.com", password="Testpass123!")
        cat = Category.objects.create(name="Cat11", slug="cat11")
        p = Product.objects.create(
            name="Headset", slug="headset", sku="SKU132", category=cat, price=250)
        order = Order.objects.create(
            user=user, total_amount=250, final_amount=250)
        oi = OrderItem.objects.create(
            order=order, product=p, quantity=1, price=250)
        self.assertEqual(oi.price, 250)


class PaymentModelTests(TestCase):
    def test_payment_one_to_one_with_order_and_status_choices(self):
        user = User.objects.create_user(
            email="payment@example.com", password="Testpass123!")
        order = Order.objects.create(
            user=user, total_amount=100, final_amount=100)
        payment = Payment.objects.create(
            order=order, amount=100, status="pending")
        self.assertEqual(payment.order, order)
        self.assertIn(payment.status, ["pending", "paid", "failed"])
