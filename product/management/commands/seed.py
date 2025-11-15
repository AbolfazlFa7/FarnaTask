from faker import Faker
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.core.management.base import BaseCommand
from product.models import (
    Category, Product, ProductImage, ProductAttribute, Cart,
    Coupon, ProductCoupon, CategoryCoupon, CartItem, ReviewImage
)
import random
from datetime import timedelta, datetime
from django.utils import timezone

fake = Faker()
User = get_user_model()


class Command(BaseCommand):
    help = 'Populates the database with realistic fake data'

    def create_users(self, count=10):
        users = [
            User(
                email=fake.unique.email(),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                password='L12345678l@!'
            ) for _ in range(count)
        ]
        User.objects.bulk_create(users)
        self.stdout.write(f"Created {count} users.")
        return list(User.objects.all())

    def create_categories(self, count=18):
        categories = []
        for _ in range(count):
            name = fake.unique.word().capitalize() + " " + fake.word().capitalize()
            slug = slugify(name, allow_unicode=True)
            parent = random.choice(
                categories) if categories and random.random() > 0.5 else None
            category = Category(name=name, slug=slug,
                                parent=parent, is_active=True)
            category.save()  # ذخیره تک‌تک برای مدیریت parent
            categories.append(category)
        self.stdout.write(f"Created {count} categories.")
        return categories

    def create_products(self, categories, count=100):
        products = []
        year = timezone.now().year
        for i in range(count):
            name = fake.unique.catch_phrase()
            slug = slugify(name, allow_unicode=True)

            product = Product(
                name=name,
                slug=slug,
                # bulk_create not call save() method
                sku=f"PRD-{year}-{i:05d}",
                category=random.choice(categories),
                description=fake.paragraph(nb_sentences=5),
                price=random.randint(2, 20000) * 10000,
                stock=random.randint(1, 100),
                is_available=True
            )
            products.append(product)
        Product.objects.bulk_create(products)

        for product in products:
            # Images
            images = [
                ProductImage(
                    product=product,
                    image=f"products/images/{fake.file_name(extension='jpg')}",
                    is_feature=(i == 0)
                ) for i in range(random.randint(1, 4))
            ]
            ProductImage.objects.bulk_create(images)

            # Attributes
            attributes = [
                ProductAttribute(
                    product=product,
                    key=fake.word().capitalize(),
                    value=fake.word().capitalize()
                ) for _ in range(random.randint(2, 10))
            ]
            ProductAttribute.objects.bulk_create(attributes)

            # Tags
            product.tags.add(*[fake.word()
                             for _ in range(random.randint(1, 4))])

            # Reviews
            for user in User.objects.all():
                review = product.reviews.create(
                    user=user,
                    rating=random.randint(1, 5),
                    title=fake.sentence(),
                    comment=fake.text(max_nb_chars=300)
                )

                review_images = [
                    ReviewImage(
                        review=review,
                        image=f"reviews/images/{fake.file_name(extension='jpg')}"
                    ) for _ in range(random.randint(1, min(5, random.randint(1, 5))))
                ]
                ReviewImage.objects.bulk_create(review_images)

        self.stdout.write(
            f"Created {count} products with images, attributes, tags, and reviews.")
        return products

    def create_coupons(self, products, categories, count=10):
        coupons = []
        for _ in range(count):
            discount_type = random.choice(['percent', 'fixed'])
            naive_start_date = fake.date_this_year()
            start_date = timezone.make_aware(
                datetime.combine(naive_start_date, datetime.min.time()))
            naive_end_date = naive_start_date + \
                timedelta(days=random.randint(10, 90))
            end_date = timezone.make_aware(
                datetime.combine(naive_end_date, datetime.min.time()))

            coupons.append(Coupon(
                code=Coupon.generate_coupon_code(),
                description=fake.sentence(),
                discount_type=discount_type,
                discount_value=random.randint(
                    5, 50) if discount_type == 'percent' else random.randint(1, 100) * 10000,
                start_date=start_date,
                end_date=end_date,
                min_order_amount=random.randint(
                    50, 500) * 10000 if random.random() > 0.7 else 0,
                max_usage=random.randint(
                    10, 500) if random.random() > 0.4 else None
            ))
        Coupon.objects.bulk_create(coupons)

        product_coupons = random.sample(products, len(products))
        category_coupons = random.sample(categories, len(categories))
        for coupon in coupons:
            if random.random() > 0.5 and product_coupons:
                ProductCoupon.objects.create(
                    product=product_coupons.pop(), coupon=coupon)
            elif category_coupons:
                CategoryCoupon.objects.create(
                    category=category_coupons.pop(), coupon=coupon)
        self.stdout.write(f"Created {count} coupons.")

    def create_cart_items(self, users, products):
        cart_items = []
        for user in users:
            cart, created = Cart.objects.get_or_create(user=user)
            product_cart = random.sample(products, k=min(
                len(products), random.randint(0, 7)))
            for product in product_cart:
                cart_items.append(CartItem(
                    cart=cart,
                    product=product,
                    quantity=random.randint(1, min(7, product.stock))
                ))
        CartItem.objects.bulk_create(cart_items)
        self.stdout.write("Created cart items.")

    def handle(self, *args, **options):
        self.stdout.write("Starting data seeding...")
        users = self.create_users()
        categories = self.create_categories()
        products = self.create_products(categories)
        self.create_coupons(products, categories)
        self.create_cart_items(users, products)
        self.stdout.write(self.style.SUCCESS(
            "Database seeding completed successfully!"))
