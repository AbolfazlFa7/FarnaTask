from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils import timezone
from taggit.managers import TaggableManager
from django.core.exceptions import ValidationError
import random
import string

User = get_user_model()


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True,
                            verbose_name=_('Name'))
    slug = models.SlugField(max_length=120, unique=True,
                            verbose_name=_('Slug'))
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True,
                               blank=True, related_name='children', verbose_name=_('Parent Category'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        ordering = ('name',)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name=_('Name'))
    slug = models.SlugField(max_length=220, unique=True,
                            verbose_name=_('Slug'))
    sku = models.CharField(max_length=20, unique=True,
                           blank=True, null=True, verbose_name=_('SKU'))
    category = models.ForeignKey(Category, on_delete=models.SET_NULL,
                                 null=True, related_name='products', verbose_name=_('Category'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    price = models.PositiveBigIntegerField(verbose_name=_('Price'))
    stock = models.PositiveIntegerField(default=0, verbose_name=_('Stock'))
    tags = TaggableManager(blank=True, verbose_name=_('Tags'))
    is_available = models.BooleanField(
        default=True, verbose_name=_('Is Available'))
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')
        ordering = ('name',)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.sku:
            year = timezone.now().year
            self.sku = f"PRD-{year}-{self.id:05d}"
            super().save(update_fields=['sku'])

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def get_final_price(self):
        now = timezone.now()
        flash_sale = self.flash_sale_items.filter(
            flash_sale__start_time__lte=now,
            flash_sale__end_time__gte=now,
            limited_stock__gt=0
        ).first()

        if not flash_sale:
            return self.price

        if flash_sale.discount_type == 'percent':
            discount = self.price * flash_sale.discount_value / 100
        else:
            discount = flash_sale.discount_value

        final_price = self.price - discount
        return max(final_price, 0)


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='images', verbose_name=_('Product')
    )
    image = models.ImageField(
        upload_to='products/images/', verbose_name=_('Image'))
    is_feature = models.BooleanField(
        default=False, verbose_name=_('Is Featured'))

    class Meta:
        verbose_name = _('Product Image')
        verbose_name_plural = _('Product Images')
        ordering = ('-is_feature',)
        constraints = [
            models.UniqueConstraint(
                fields=['product'],
                condition=models.Q(is_feature=True),
                name='unique_featured_image_per_product'
            ),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.image.name}"


class ProductAttribute(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                related_name='attributes', verbose_name=_('Product'))
    key = models.CharField(max_length=100, verbose_name=_('Key'))
    value = models.CharField(max_length=100, verbose_name=_('Value'))

    class Meta:
        verbose_name = _('Product Attribute')
        verbose_name_plural = _('Product Attributes')
        ordering = ('key',)

    def __str__(self):
        return self.key


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name=_('Code'))
    description = models.CharField(
        max_length=255, blank=True, verbose_name=_('Description'))
    discount_type = models.CharField(
        max_length=10,
        choices=[('percent', _('Percentage')), ('fixed', _('Fixed Amount'))],
        default='percent',
        verbose_name=_('Discount Type')
    )
    discount_value = models.PositiveBigIntegerField(
        verbose_name=_('Discount Value'))
    start_date = models.DateTimeField(verbose_name=_('Start Date'))
    end_date = models.DateTimeField(
        null=True, blank=True, verbose_name=_('End Date'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    min_order_amount = models.PositiveBigIntegerField(
        default=0, verbose_name=_('Minimum Order Amount'))
    max_usage = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_('Max Usage'))
    usage_count = models.PositiveIntegerField(
        default=0, verbose_name=_('Usage Count'))

    class Meta:
        verbose_name = _('Coupon')
        verbose_name_plural = _('Coupons')

    def __str__(self):
        return f"{self.code} - {self.discount_value}{'%' if self.discount_type == 'percent' else ''}"

    @staticmethod
    def generate_coupon_code(length=10) -> str:
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choices(chars, k=length))

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_coupon_code()
        super().save(*args, **kwargs)

    def clean(self):
        if self.discount_type == 'percent' and not (0 <= self.discount_value <= 100):
            raise ValidationError(
                _('Discount percentage must be between 0 and 100.'))


class ProductCoupon(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='coupons', verbose_name=_('Product'))
    coupon = models.ForeignKey(
        Coupon, on_delete=models.CASCADE, related_name='products', verbose_name=_('Coupon'))

    class Meta:
        verbose_name = _('Product Coupon')
        verbose_name_plural = _('Product Coupons')
        ordering = ('coupon',)

    def __str__(self):
        return f"{self.product.name} - {self.coupon.code}"


class CategoryCoupon(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='coupons', verbose_name=_('Category'))
    coupon = models.ForeignKey(
        Coupon, on_delete=models.CASCADE, related_name='categories', verbose_name=_('Coupon'))

    class Meta:
        verbose_name = _('Category Coupon')
        verbose_name_plural = _('Category Coupons')
        ordering = ('coupon',)

    def __str__(self):
        return f"{self.category.name} - {self.coupon.code}"


class UserCoupon(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='coupons', verbose_name=_('User'))
    coupon = models.ForeignKey(
        Coupon, on_delete=models.CASCADE, related_name='users', verbose_name=_('Coupon'))


class Review(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='reviews', verbose_name=_('Product'))
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='reviews', verbose_name=_('User'))
    rating = models.PositiveSmallIntegerField(verbose_name=_(
        'Rating'), choices=[(i, i) for i in range(1, 6)])
    title = models.CharField(max_length=100, verbose_name=_('Title'))
    comment = models.TextField(verbose_name=_('Comment'))
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Review')
        verbose_name_plural = _('Reviews')
        unique_together = ('product', 'user')
        ordering = ('rating',)

    def __str__(self):
        return f'{self.user.email} - {self.product.name} - {self.rating}'


class ReviewImage(models.Model):
    review = models.ForeignKey(
        Review, on_delete=models.CASCADE, related_name='images', verbose_name=_('Review'))
    image = models.ImageField(
        upload_to='reviews/images/', verbose_name=_('Image'))

    class Meta:
        verbose_name = _('Product Image')
        verbose_name_plural = _('Product Images')

    def save(self, *args, **kwargs):
        if self.review.images.count() >= 5 and not self.pk:
            raise ValidationError("Maximum 5 images are allowed per review.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.review.product.name}"


class Cart(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='cart', null=True, verbose_name=_('User'))
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Cart')
        verbose_name_plural = _('Carts')

    def __str__(self):
        return f"Cart {self.id} - {self.user}"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name='items', verbose_name=_('Cart'))
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='cart_items', verbose_name=_('Product'))
    quantity = models.PositiveSmallIntegerField(
        default=1, verbose_name=_('Quantity'))

    class Meta:
        verbose_name = _('Cart Item')
        verbose_name_plural = _('Cart Items')
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"

    def save(self, *args, **kwargs):
        if self.product.stock < self.quantity:
            self.quantity = self.product.stock

        return super().save()


class Order(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='orders', verbose_name=_('User'))
    tracking_code = models.CharField(
        max_length=50, blank=True, unique=True, verbose_name=_('Tracking Code'))
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name=_('Updated At'))
    status = models.CharField(
        max_length=9,
        choices=[
            ('pending', _('Pending')),
            ('paid', _('Paid')),
            ('shipped', _('Shipped')),
            ('completed', _('Completed')),
            ('canceled', _('Canceled')),
        ],
        default='pending',
        verbose_name=_('Status')
    )
    total_amount = models.PositiveBigIntegerField(
        verbose_name=_('Total Amount'))
    discount_amount = models.PositiveBigIntegerField(
        null=True, blank=True, default=0, verbose_name=_('Discount Amount'))
    final_amount = models.PositiveBigIntegerField(
        verbose_name=_('Final Amount'))
    coupon_code = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        verbose_name = _('Order')
        verbose_name_plural = _('Orders')

    def __str__(self):
        return f"Order {self.id} - {self.user}"

    def save(self, *args, **kwargs):
        if not self.tracking_code and self.status == 'pending':
            today = timezone.now().strftime('%Y%m%d')
            last_order = Order.objects.filter(
                tracking_code__startswith=f"ORD-{today}-"
            ).order_by('-tracking_code').first()
            serial = 1
            if last_order:
                serial = int(last_order.tracking_code.split('-')[-1]) + 1
            self.tracking_code = f"ORD-{today}-{serial:03d}"
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items', verbose_name=_('Order'))
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, verbose_name=_('Product'))
    quantity = models.PositiveSmallIntegerField(
        default=1, verbose_name=_('Quantity'))
    price = models.PositiveBigIntegerField(verbose_name=_('Price'))

    class Meta:
        verbose_name = _('Order Item')
        verbose_name_plural = _('Order Items')

    def __str__(self):
        return f"{self.product} --> {self.quantity}"


class Payment(models.Model):
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name='payment', verbose_name=_('Order'))
    amount = models.PositiveBigIntegerField(verbose_name=_('Amount'))
    method = models.CharField(
        max_length=10,
        choices=[
            ('card', _('Card'))
        ],
        verbose_name=_('Payment Method')
    )
    status = models.CharField(
        max_length=20,
        choices=[('pending', _('Pending')), ('success',
                                             _('Success')), ('failed', _('Failed'))],
        default='pending',
        verbose_name=_('Status')
    )
    transaction_id = models.CharField(
        max_length=255, blank=True, verbose_name=_('Transaction ID'))
    tracking_code = models.CharField(
        max_length=50, unique=True, blank=True, verbose_name=_('Tracking Code'))
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_('Created At'))

    class Meta:
        verbose_name = _('Payment')
        verbose_name_plural = _('Payments')

    def __str__(self):
        return f"Payment {self.id} - {self.status}"

    def save(self, *args, **kwargs):
        if not self.tracking_code and self.status == 'pending':
            today = timezone.now().strftime('%Y%m%d')
            last_payment = Payment.objects.filter(
                tracking_code__startswith=f"PAY-{today}-"
            ).order_by('-tracking_code').first()
            serial = 1
            if last_payment:
                serial = int(last_payment.tracking_code.split('-')[-1]) + 1
            self.tracking_code = f"PAY-{today}-{serial:03d}"
        super().save(*args, **kwargs)


class FlashSale(models.Model):
    title = models.CharField(max_length=150)
    start_time = models.DateTimeField(null=False, blank=False)
    end_time = models.DateTimeField(null=False, blank=False)

    def is_running(self):
        now = timezone.now()
        return self.start_time <= now <= self.end_time

    def __str__(self):
        return self.title


class FlashSaleProduct(models.Model):
    flash_sale = models.ForeignKey(
        FlashSale, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(
        Product, related_name='flash_sale_items', on_delete=models.CASCADE)
    discount_type = models.CharField(
        max_length=10,
        choices=[('percent', _('Percentage')), ('fixed', _('Fixed Amount'))],
        default='percent',
        verbose_name=_('Discount Type'),
        null=False, blank=False)
    discount_value = models.PositiveBigIntegerField(
        verbose_name=_('Discount Value'), null=False, blank=False)
    limited_stock = models.PositiveIntegerField(default=0,
                                                help_text="limitted stock for flash sale")

    class Meta:
        unique_together = ('flash_sale', 'product')

    def __str__(self):
        return f"{self.product} in {self.flash_sale}"

    def clean(self):
        if self.discount_type == 'percent' and not (0 <= self.discount_value <= 100):
            raise ValidationError(
                _('Discount percentage must be between 0 and 100.'))

    def get_active_flash_sale(self):
        now = timezone.now()
        return self.flash_sale_items.filter(
            flash_sale__start_time__lte=now,
            flash_sale__end_time__gte=now
        ).order_by('flash_sale__start_time').first()
