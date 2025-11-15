from rest_framework.views import APIView
from .serializers import OrderSerializer, OrderDetailSerializer, PaymentSerializer, AdminOrderSerializer
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status
from rest_framework.serializers import ValidationError
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .utils.coupon_service import verify_coupon
from .utils.zarinpal import request_payment, verify_payment
from django.db.models import Prefetch, Count, Sum, F
from django.db import transaction
from django.db.utils import IntegrityError
from .serializers import (
    CategorySerializer, AdminCategorySerializer, ProductSerializer, ProductDetailSerializer,
    AdminProductSerializer, AdminProductAttributeSerializer, AdminProductImageSerializer,
    CouponSerializer, AdminCouponSerializer, AdminCategoryCouponSerializer, AdminProductCouponSerializer,
    ReviewSerializer, ReviewImageSerializer, AdminReviewSerializer, AdminReviewImageSerializer,
    CartItemsListSerializer, CartItemsCreateSerializer, AdminPaymentSerializer, AdminUserCouponSerializer,
    CartItemsUpdateSerializer, FlashSaleSerializer
)
from .models import (
    Product, Category, ProductAttribute, Review,
    ProductImage, Coupon, ProductCoupon, CategoryCoupon, UserCoupon,
    ReviewImage, Cart, CartItem, Order, Payment, OrderItem, FlashSale, FlashSaleProduct
)
from rest_framework.generics import (
    ListAPIView, RetrieveAPIView, CreateAPIView, UpdateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from .filters import ProductListFilter
from django.utils import timezone
from django.db.models import Prefetch, Count, Sum, F, Case, When, IntegerField


# Category Section
class CategoryList(ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer


class AdminCategoryMangement(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = AdminCategorySerializer
    permission_classes = [IsAdminUser]
# ______________________________________


# Product Section
class ProductList(ListAPIView):
    serializer_class = ProductSerializer
    filterset_class = ProductListFilter

    def get_queryset(self):
        now = timezone.now()
        return (
            Product.objects.filter(is_available=True)
            .annotate(
                final_price=Case(
                    When(
                        flash_sale_items__flash_sale__start_time__lte=now,
                        flash_sale_items__flash_sale__end_time__gte=now,
                        flash_sale_items__limited_stock__gt=0,
                        flash_sale_items__discount_type='percent',
                        then=(
                            F('price') * (100 - F('flash_sale_items__discount_value')) / 100)
                    ),
                    When(
                        flash_sale_items__flash_sale__start_time__lte=now,
                        flash_sale_items__flash_sale__end_time__gte=now,
                        flash_sale_items__limited_stock__gt=0,
                        flash_sale_items__discount_type='fixed',
                        then=(F('price') - F('flash_sale_items__discount_value'))
                    ),
                    default=F('price'),
                    output_field=IntegerField()
                )
            )
            .prefetch_related(
                'attributes',
                'reviews',
                Prefetch('images', queryset=ProductImage.objects.filter(
                    is_feature=True))
            )
            .annotate(carts_count=Count('cart_items'))
            .defer('description')
        )


class ProductDetail(RetrieveAPIView):
    queryset = (Product.objects.filter(is_available=True)
                .annotate(carts_count=Count('cart_items'))
                .select_related('category',)
                .prefetch_related('attributes', 'reviews', 'images')
                )
    serializer_class = ProductDetailSerializer
    lookup_field = 'slug'
    filterset_fields = {
        'reviews__rating': ['exact', 'gt', 'lt', 'gte', 'lte'],
        'reviews__user__id': ['exact'],
        'reviews__created_at': ['exact', 'gt', 'lt', 'gte', 'lte'],
    }


class AdminProductMangement(ModelViewSet):
    queryset = Product.objects.all().order_by('pk')
    serializer_class = AdminProductSerializer
    permission_classes = [IsAdminUser]
    filterset_class = ProductListFilter


class AdminProductImageMangement(ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = AdminProductImageSerializer
    permission_classes = [IsAdminUser]
    parser_classes = (MultiPartParser, FormParser)


class AdminProductAttributeMangement(ModelViewSet):
    queryset = ProductAttribute.objects.all()
    serializer_class = AdminProductAttributeSerializer
    permission_classes = [IsAdminUser]
# ______________________________________


# Coupon Section
class CoupenVerify(CreateAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Verify coupon code",
        summary="Verify Coupon",
        request=CouponSerializer,
        responses={
            200: OpenApiResponse(
                description="Coupon has been verified",
                response={
                    'type': 'object',
                    'properties': {
                        'status': {
                            'type': 'string',
                        },
                        'cart_amount': {
                            'type': 'integer',
                        },
                        'coupon_type': {
                            'type': 'choice',
                            'enum': ['percentage', 'fixed'],
                        },
                        'coupon_value': {
                            'type': 'integer',
                        },
                        'coupon_code': {
                            'type': 'string',
                        },
                        'final_amount': {
                            'type': 'integer',
                        },
                    },
                    'required': ['status', 'cart_amount', 'coupon_type', 'coupon_value', 'coupon_code', 'final_amount'],
                },
                examples=[
                    OpenApiExample(
                        name="Success Response",
                        value={
                            'status': 'Coupon is valid',
                            'cart_amount': 2000,
                            'coupon_type': 'percentage',
                            'coupon_value': 50,
                            'coupon_code': 'ABCDEF74',
                            'final_amount': 1000,
                        },
                    )
                ]
            ),
            400: OpenApiResponse(
                description="Coupon is not valid",
                response=dict,
                examples=[
                    OpenApiExample(
                        name="Invalid coupon code",
                        description="such coupon does not exist",
                        value={
                            'status': 'Invalid coupon code'
                        },
                    ),
                    OpenApiExample(
                        name="Coupon is not active",
                        description="coupon is not active",
                        value={
                            'status': 'Coupon is not active'
                        },
                    ),
                    OpenApiExample(
                        name="Coupon expired",
                        description="coupon time has expired",
                        value={
                            'status': 'Coupon expired or not valid yet'
                        },
                    ),
                    OpenApiExample(
                        name="Coupon usage limit reached",
                        description="coupon usage limit reached",
                        value={
                            'status': 'Coupon usage limit reached'
                        },
                    ),
                    OpenApiExample(
                        name="Cart is empty",
                        description="User cart is empty",
                        value={
                            'status': 'Cart is empty'
                        },
                    ),
                    OpenApiExample(
                        name="Cart amount less than minimum amount required for this coupon",
                        description="cart amount less than minimum amount required for this coupon",
                        value={
                            'status': 'Cart amount less than minimum amount required for this coupon'
                        },
                    ),
                    OpenApiExample(
                        name="Coupon does not apply to products in the order",
                        description="coupon does not apply to products in the order",
                        value={
                            'status': 'Coupon does not apply to products in the order'
                        },
                    ),
                    OpenApiExample(
                        name="Coupon does not apply to categories of products in the order",
                        description="coupon does not apply to categories of products in the order",
                        value={
                            'status': 'Coupon does not apply to categories of products in the order'
                        },
                    ),
                    OpenApiExample(
                        name="Coupon does not apply to this user",
                        description="coupon does not apply to this user",
                        value={
                            'status': 'Coupon does not apply to this user'
                        },
                    ),

                ]
            )
        }
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = self.request.user
        code = serializer.data.get('code')

        status_code, response_data = verify_coupon(user, code)
        return Response(response_data, status=status_code)


class AdminCouponMangement(ModelViewSet):
    queryset = Coupon.objects.all().prefetch_related('products', 'categories')
    serializer_class = AdminCouponSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = {
        'code': ['exact'],
        'discount_type': ['exact'],
        'discount_value': ['exact'],
        'start_date': ['exact'],
        'end_date': ['exact'],
    }


class AdminCategoryCouponMangement(ModelViewSet):
    queryset = CategoryCoupon.objects.all()
    serializer_class = AdminCategoryCouponSerializer
    permission_classes = [IsAdminUser]


class AdminProductCouponMangement(ModelViewSet):
    queryset = ProductCoupon.objects.all()
    serializer_class = AdminProductCouponSerializer
    permission_classes = [IsAdminUser]


class AdminUserCouponMangement(ModelViewSet):
    queryset = UserCoupon.objects.all()
    serializer_class = AdminUserCouponSerializer
    permission_classes = [IsAdminUser]

# ______________________________________


# Review Section
class ReviewCreate(CreateAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(
            data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)

        try:
            serializer.save()

        except IntegrityError as e:
            return Response({'status': 'You have already reviewed this product'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ReviewUpdate(UpdateAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        serializer.fields.pop('product', None)
        if self.request.method == 'PATCH':
            serializer.fields['rating'].required = False
            serializer.fields['title'].required = False
            serializer.fields['comment'].required = False
        return serializer

    def put(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, instance=self.get_object(), context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, instance=self.get_object(), context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class ReviweImageCreate(CreateAPIView):
    queryset = ReviewImage.objects.all()
    serializer_class = ReviewImageSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)


class AdminReviewCreate(ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = AdminReviewSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = {
        'rating': ['exact', 'gt', 'lt', 'gte', 'lte'],
        'user__id': ['exact'],
    }


class AdminReviewImageCreate(ModelViewSet):
    queryset = ReviewImage.objects.all()
    serializer_class = AdminReviewImageSerializer
    permission_classes = [IsAdminUser]
    parser_classes = (MultiPartParser, FormParser)
# ______________________________________


# Cart Section
class UserCartList(ListAPIView):
    serializer_class = CartItemsListSerializer
    permission_classes = [IsAuthenticated]
    queryset = CartItem.objects.none()  # just for swagger

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.none()
        return (
            CartItem.objects
            .filter(cart__user=self.request.user)
            .select_related('product')
            .prefetch_related(
                Prefetch(
                    'product__images',
                    queryset=ProductImage.objects.filter(is_feature=True),
                    to_attr='prefetched_feature_image'
                ),
                Prefetch(
                    'product__cart_items',
                    queryset=CartItem.objects.all(),
                    to_attr='prefetched_cart_items'
                )
            )
        )


class UserCartItemCreate(CreateAPIView):
    serializer_class = CartItemsCreateSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Add Product to Cart",
        description="Add unique product to cart of user",
        request=CartItemsCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=dict,
                description="Product added to cart successfully",
                examples=[
                    OpenApiExample(
                        name="Success Response",
                        value={
                            "id": 1,
                            "product_id": 1,
                            "quantity": 1,
                        },
                    )
                ]
            ),
            400: OpenApiResponse(
                description="Product already added to cart",
                response=dict,
                examples=[
                    OpenApiExample(
                        name="Product already added to cart",
                        description="Product already added to cart",
                        value={
                            "error": "Product already added to cart"
                        },
                    ),
                ]
            ),
        }
    )
    def post(self, request):
        try:
            return super().post(request)
        except IntegrityError as e:
            return Response({'error': 'Product already added to cart'}, status=status.HTTP_400_BAD_REQUEST)


class UserCartItemDetail(RetrieveUpdateDestroyAPIView):
    serializer_class = CartItemsUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user)


class AdminCartItemCreate(ModelViewSet):
    queryset = CartItem.objects.all()
    serializer_class = CartItemsCreateSerializer
    permission_classes = [IsAdminUser]
# ______________________________________


# Order Section
class CreateOrderView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def perform_create(self, serializer):
        coupon = serializer.validated_data.get('coupon')
        if coupon:
            user = self.request.user
            status_code, response_data = verify_coupon(
                user, coupon)

            if status_code != 200:
                raise ValidationError(response_data)

            else:
                cart = response_data.get('cart')
                cart_amount = response_data.get('cart_amount')
                coupon_value = response_data.get('coupon_value')
                final_amount = response_data.get('final_amount')
        else:
            user = self.request.user
            now = timezone.now()
            cart_qs = Cart.objects.filter(user=user).prefetch_related(
                Prefetch(
                    'items',
                    queryset=CartItem.objects.select_related('product__category').prefetch_related(
                        Prefetch(
                            'product__flash_sale_items',
                            queryset=FlashSaleProduct.objects.select_related('flash_sale').filter(
                                flash_sale__start_time__lte=now,
                                flash_sale__end_time__gte=now
                            ),
                            to_attr='active_flash_sales'
                        )
                    )
                )
            )
            cart = cart_qs.first()
            if not cart.items.exists():
                return Response({'error': 'Cart is empty'}, status=400)

            cart_amount = cart.items.aggregate(total_amount=Sum(
                F('quantity') * F('product__price')))['total_amount']

            discount_amount = 0
            for item in cart.items.all():
                if getattr(item.product, 'active_flash_sales', None):
                    for fs in item.product.active_flash_sales:
                        if fs.discount_type == 'percent':
                            discount_per_unit = item.product.price * \
                                (fs.discount_value / 100)
                        else:
                            discount_per_unit = fs.discount_value
                        discount_amount += discount_per_unit * item.quantity
                        break

            final_amount = cart_amount - discount_amount

        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                total_amount=cart_amount,
                discount_amount=discount_amount,
                final_amount=final_amount,
                coupon_code=coupon if coupon else None
            )

            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.get_final_price()
                )

            authority, payment_url = request_payment(
                order.final_amount,
                f'Payment for order {order.id}',
                order.id
            )
            if not authority:
                raise ValidationError({'error': 'Failed to initiate payment'})

            Payment.objects.create(
                order=order,
                amount=order.final_amount,
                method='card',
                status='pending',
                transaction_id=authority
            )

            self.payment_url = payment_url

    @extend_schema(
        description="A callback for creating order",
        summary="Create Order",
        responses={
            200: OpenApiResponse(
                response=dict,
                description="User Must redirect to payment url",
                examples=[
                    OpenApiExample(
                        name="Success Response",
                        value={
                            "payment_url": "example.com"
                        },
                    )
                ]
            ),

            400: OpenApiResponse(
                description="Coupon is not valid",
                response=dict,
                examples=[
                    OpenApiExample(
                        name="Authority from payment is not valid",
                        description="it is a server side error,if zarinpal api get error",
                        value={'error': 'Failed to initiate payment'}
                    ),
                    OpenApiExample(
                        name="Invalid coupon code",
                        description="such coupon does not exist",
                        value={
                            'status': 'Invalid coupon code'
                        },
                    ),
                    OpenApiExample(
                        name="Coupon is not active",
                        description="coupon is not active",
                        value={
                            'status': 'Coupon is not active'
                        },
                    ),
                    OpenApiExample(
                        name="Coupon expired",
                        description="coupon time has expired",
                        value={
                            'status': 'Coupon expired or not valid yet'
                        },
                    ),
                    OpenApiExample(
                        name="Coupon usage limit reached",
                        description="coupon usage limit reached",
                        value={
                            'status': 'Coupon usage limit reached'
                        },
                    ),
                    OpenApiExample(
                        name="Cart is empty",
                        description="User cart is empty",
                        value={
                            'status': 'Cart is empty'
                        },
                    ),
                    OpenApiExample(
                        name="Cart amount less than minimum amount required for this coupon",
                        description="cart amount less than minimum amount required for this coupon",
                        value={
                            'status': 'Cart amount less than minimum amount required for this coupon'
                        },
                    ),
                    OpenApiExample(
                        name="Coupon does not apply to products in the order",
                        description="coupon does not apply to products in the order",
                        value={
                            'status': 'Coupon does not apply to products in the order'
                        },
                    ),
                    OpenApiExample(
                        name="Coupon does not apply to categories of products in the order",
                        description="coupon does not apply to categories of products in the order",
                        value={
                            'status': 'Coupon does not apply to categories of products in the order'
                        },
                    ),
                    OpenApiExample(
                        name="Coupon does not apply to this user",
                        description="coupon does not apply to this user",
                        value={
                            'status': 'Coupon does not apply to this user'
                        },
                    ),

                ]
            )
        }
    )
    def post(self, request):
        response = super().post(request)
        response.data['payment_url'] = getattr(self, 'payment_url', None)
        return response


class OrderListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer
    queryset = Order.objects.none()  # just for swagger
    filterset_fields = {
        'status': ['exact'],
        'total_amount': ['exact', 'gt', 'lt', 'gte', 'lte'],
    }

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.none()
        return Order.objects.filter(user=self.request.user).select_related('user')


class OrderDetailView(RetrieveAPIView):
    queryset = Order.objects.all().prefetch_related(
        'items').select_related('payment')
    permission_classes = [IsAuthenticated]
    serializer_class = OrderDetailSerializer


class AdminOrderView(ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = AdminOrderSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = {
        'status': ['exact'],
        'tracking_code': ['exact'],
        'total_amount': ['exact', 'gt', 'lt', 'gte', 'lte'],
        'discount_amount': ['exact', 'gt', 'lt', 'gte', 'lte'],
        'final_amount': ['exact', 'gt', 'lt', 'gte', 'lte'],
        'created_at': ['exact'],
        'updated_at': ['exact'],
        'user__id': ['exact'],
    }
# ______________________________________


# Payment Section
class PaymentVerifyView(APIView):

    @extend_schema(
        description="A callback for verifying payment",
        summary="Verify Payment",
        responses={
            200: OpenApiResponse(
                response=dict,
                description="Payment verified successfully",
                examples=[
                    OpenApiExample(
                        name="Success Response",
                        value={
                            "status": "Payment Successful"
                        },
                    )
                ]
            ),
            400: OpenApiResponse(
                response=dict,
                description="Error in verifying payment",
                examples=[
                    OpenApiExample(
                        name="Invalid Payment",
                        value={
                            "status": "Invalid payment"
                        },
                    ),
                    OpenApiExample(
                        name="Payment Canceled or Failed",
                        value={
                            "status": "Payment canceled or failed"
                        },
                    ),
                    OpenApiExample(
                        name="Payment Failed",
                        value={
                            "status": "Payment failed"
                        },
                    ),
                ]
            ),
        }
    )
    @transaction.atomic
    def get(self, request):
        authority = request.query_params.get('Authority')
        status_param = request.query_params.get('Status')
        payment = Payment.objects.select_for_update().filter(...).prefetch_related(
            'order__items__product__flash_sale_items__flash_sale'
        ).first()

        if not payment:
            return Response({'error': 'Invalid payment'}, status=status.HTTP_400_BAD_REQUEST)

        if status_param == 'NOK':
            payment.status = 'failed'
            payment.order.status = 'canceled'
            payment.save()
            payment.order.save()
            return Response({'status': 'Payment canceled or failed'}, status=status.HTTP_400_BAD_REQUEST)

        ref_id, verify_status = verify_payment(authority, payment.amount)
        if verify_status == 'success':
            payment.status = 'success'
            payment.transaction_id = ref_id
            payment.save()

            payment.order.status = 'paid'
            payment.order.save()

            cart = payment.order.user.cart
            cart.items.all().delete()

            if payment.order.discount_amount > 0:
                if payment.order.coupon_code:
                    Coupon.objects.select_for_update().filter(
                        code=payment.order.coupon_code
                    ).update(usage_count=F('usage_count') + 1)
                else:
                    for item in payment.order.items.select_related('product'):
                        fs = (
                            FlashSaleProduct.objects
                            .select_for_update()
                            .get(product=item.product)
                        )

                        fs.limited_stock = F('limited_stock') - 1
                        fs.save(update_fields=['limited_stock'])

            return Response({'status': 'Payment Successful', 'ref_id': ref_id}, status=status.HTTP_200_OK)

        else:
            payment.status = 'failed'
            payment.save()
            order = payment.order
            order.status = 'canceled'
            order.save()
            return Response({'status': 'Payment failed'}, status=status.HTTP_400_BAD_REQUEST)


class PaymentListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer
    queryset = Payment.objects.none()  # just for swagger
    filterset_fields = {
        'status': ['exact'],
    }

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.none()
        return Payment.objects.filter(order__user=self.request.user)


class AdminPaymentView(ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = AdminPaymentSerializer
    queryset = Payment.objects.all()
    filterset_fields = {
        'status': ['exact'],
        'method': ['exact'],
        'amount': ['exact', 'gt', 'lt', 'gte', 'lte'],
        'tracking_code': ['exact'],
        'order__user__id': ['exact'],
    }
# ______________________________________


# Flash Sale Section
class FlashSaleView(ListAPIView):
    serializer_class = FlashSaleSerializer

    def get_queryset(self):
        now = timezone.now()
        queryset = (
            FlashSale.objects.filter(
                start_time__lte=now,
                end_time__gte=now,
            )
            .prefetch_related(
                Prefetch(
                    'items',
                    queryset=FlashSaleProduct.objects.select_related('product')
                )
            )
        )
        return queryset
