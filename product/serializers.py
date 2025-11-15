from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema_field
from .models import (
    Category, Product, ProductImage, ProductAttribute,
    Coupon, CategoryCoupon, ProductCoupon, UserCoupon, Review,
    ReviewImage, CartItem, Order, OrderItem, Payment, Cart, FlashSaleProduct, FlashSale
)

User = get_user_model()


# Category Section
class AdminCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        exclude = ['is_active']
# ______________________________________


# Product Section
class ProductSerializer(serializers.ModelSerializer):
    carts_count = serializers.IntegerField()
    image = serializers.SerializerMethodField()
    final_price = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'url', 'name', 'slug', 'sku',
                  'price', 'final_price', 'stock', 'carts_count', 'image',]
        depth = 1
        extra_kwargs = {
            'url': {'view_name': 'product-detail', 'lookup_field': 'slug'},
        }

    @extend_schema_field(serializers.URLField)
    def get_image(self, obj):
        if obj.images.exists():
            return obj.images.first().image.url


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['image']


class ProductAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAttribute
        fields = ['key', 'value']


class ProductReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['user', 'rating', 'title', 'comment', 'created_at']


class ProductDetailSerializer(serializers.ModelSerializer):
    carts_count = serializers.IntegerField()
    images = ProductImageSerializer(many=True, read_only=True)
    attributes = ProductAttributeSerializer(many=True, read_only=True)
    reviews = ProductReviewSerializer(many=True, read_only=True)
    final_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['name', 'slug', 'price', 'final_price', 'stock', 'carts_count', 'category',
                  'description', 'images', 'attributes', 'reviews']

    @extend_schema_field(serializers.IntegerField)
    def get_final_price(self, obj):
        return obj.get_final_price()


class AdminProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class AdminProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = '__all__'


class AdminProductAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAttribute
        fields = '__all__'
# ______________________________________


# Coupon Section
class CouponSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50, required=True)


class AdminCouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['code', 'description', 'discount_type', 'discount_value',
                  'start_date', 'end_date', 'is_active', 'min_order_amount', 'max_usage', 'usage_count', 'products', 'categories']

    def get_products(self, obj):
        return Product.objects.filter(coupons__coupon=obj).values('id', 'slug')

    def get_categories(self, obj):
        return Category.objects.filter(coupons__coupon=obj).values('id', 'slug')

    def validate(self, data):
        instance = Coupon(**data)

        if self.instance:
            for field in self.instance._meta.fields:
                field_name = field.name
                if field_name not in data:
                    setattr(instance, field_name, getattr(
                        self.instance, field_name))

        try:
            instance.full_clean()
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict)

        return data


class AdminCategoryCouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryCoupon
        fields = '__all__'


class AdminProductCouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCoupon
        fields = '__all__'


class AdminUserCouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCoupon
        fields = '__all__'
# ______________________________________


# Review Section
class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['product', 'rating', 'title', 'comment']

    def create(self, validated_data):
        product = validated_data.get('product')
        user = self.context['user']
        rating = validated_data.get('rating')
        title = validated_data.get('title')
        comment = validated_data.get('comment')
        review = Review.objects.create(
            product=product, user=user, rating=rating, title=title, comment=comment)
        return review

    def update(self, instance, validated_data):
        if instance.user == self.context['user']:
            instance.rating = validated_data.get('rating', instance.rating)
            instance.title = validated_data.get('title', instance.title)
            instance.comment = validated_data.get('comment', instance.comment)
            instance.save()
            return instance
        else:
            raise PermissionDenied


class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = '__all__'


class AdminReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = '__all__'


class AdminReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = '__all__'
# ______________________________________


# Cart Section
class CartProductSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    carts_count = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ProductSerializer.Meta.fields
        extra_kwargs = {
            'url': {'view_name': 'product-detail', 'lookup_field': 'slug'},
        }

    @extend_schema_field(serializers.URLField)
    def get_image(self, obj):
        if obj.prefetched_feature_image:
            return obj.prefetched_feature_image[0].image.url
        return None

    @extend_schema_field(serializers.IntegerField)
    def get_carts_count(self, obj):
        if hasattr(obj, 'prefetched_cart_items'):
            return len(obj.prefetched_cart_items)
        return obj.cart_items.count()

    @extend_schema_field(serializers.IntegerField)
    def get_final_price(self, obj):
        return obj.get_final_price()


class CartItemsListSerializer(serializers.ModelSerializer):
    product = CartProductSerializer()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'url']
        extra_kwargs = {
            'url': {'view_name': 'cart-item-detail', 'lookup_field': 'pk'},
        }
        depth = 1

    def validate(self, attrs):
        quantity = attrs.get('quantity')
        product = attrs.get('product')

        if quantity > product.stock:
            raise serializers.ValidationError(
                {'quantity': _('Quantity can not be greater than stock')})
        return attrs


class CartItemsCreateSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(required=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product_id', 'quantity']

    def validate(self, attrs):
        quantity = attrs.get('quantity')
        product_id = attrs.get('product_id')

        if product_id > 0:
            product = (
                Product.objects.filter(id=product_id)
                .only('stock')
                .first()
            )
        else:
            raise serializers.ValidationError(
                {'product_id': _('Product id not valid')})

        if not product:
            raise serializers.ValidationError(
                {'product_id': _('Product not found')})

        if quantity > product.stock:
            raise serializers.ValidationError(
                {'quantity': _('Quantity can not be greater than stock')})

        product_fst = product.flash_sale_items.first()  # later add an is active on model
        if product_fst:
            if product_fst.flash_sale.is_running() and product_fst.limited_stock > 0:
                if quantity > 1:
                    raise serializers.ValidationError(
                        {'quantity': _('Quantity of flash sale products can not be more then 1')})
        return {'product': product, 'quantity': quantity}

    def create(self, validated_data):
        user = self.context['request'].user
        cart, _ = Cart.objects.get_or_create(user=user)
        return CartItem.objects.create(
            cart=cart,
            product=validated_data['product'],
            quantity=validated_data['quantity']
        )


class CartItemsUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['id', 'quantity']

    def validate_quantity(self, quantity):
        cart_item = self.instance
        product = cart_item.product

        if cart_item.quantity == quantity:
            return quantity

        if quantity > product.stock:
            raise serializers.ValidationError(
                _('Quantity cannot be greater than stock')
            )

        product_fst = product.flash_sale_items.first()  # later add an is active on model
        if product_fst.flash_sale.is_running() and product_fst.limited_stock > 0:
            if quantity > 1:
                raise serializers.ValidationError(
                    {'error': _('Quantity of flash sale products can not be more then 1')})

        return quantity

# ______________________________________


# Order Section
class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'price']


class OrderSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    payment_method = serializers.ChoiceField(
        choices=Payment._meta.get_field('method').choices,
        default='card', write_only=True
    )
    coupon = serializers.CharField(
        required=False, max_length=50, write_only=True)

    class Meta:
        model = Order
        fields = ['id', 'user', 'created_at', 'updated_at',
                  'status', 'total_amount', 'discount_amount', 'final_amount', 'tracking_code', 'items', 'payment_method', 'coupon']
        read_only_fields = ['user', 'created_at', 'updated_at', 'status',
                            'total_amount', 'discount_amount', 'final_amount', 'tracking_code', 'items',]
        extra_kwargs = {
            'url': {'view_name': 'order-detail', 'lookup_field': 'pk'},
        }


class OrderDetailSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    payment = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'user', 'created_at', 'updated_at', 'status',
                  'total_amount', 'tracking_code', 'items', 'payment']
        read_only_fields = ['created_at',
                            'updated_at', 'tracking_code', 'user']

    @extend_schema_field(serializers.DictField)
    def get_payment(self, obj):
        try:
            payment = obj.payment
            return PaymentSerializer(payment).data
        except Payment.DoesNotExist:
            return None


class AdminOrderSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    payment = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = '__all__'

    @extend_schema_field(serializers.DictField)
    def get_payment(self, obj):
        try:
            payment = obj.payment
            return PaymentSerializer(payment).data
        except Payment.DoesNotExist:
            return None


class AdminPaymentSerializer(serializers.ModelSerializer):
    order = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Payment
        fields = '__all__'
# ______________________________________


# Payment Section
class PaymentSerializer(serializers.ModelSerializer):
    order = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'order', 'amount', 'method',
                  'status', 'tracking_code', 'created_at']
        read_only_fields = ['order', 'amount',
                            'tracking_code', 'method', 'created_at', 'status']
# ______________________________________


# Flash Sale Section
class FlashSaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlashSaleProduct
        fields = ['id', 'discount_type',
                  'discount_value', 'limited_stock', 'product']
        depth = 1


class FlashSaleSerializer(serializers.ModelSerializer):
    items = FlashSaleItemSerializer(many=True, read_only=True)

    class Meta:
        model = FlashSale
        fields = ['id', 'title', 'start_time', 'end_time', 'items']
