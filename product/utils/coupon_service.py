from product.models import Coupon, Cart, CartItem, FlashSaleProduct
from django.utils import timezone
from django.db.models import Prefetch, F, Sum


def verify_coupon(user, code, system=False):
    """
    system: it is for system verify coupon, to execute less queries
    """

    now = timezone.now()

    coupon = Coupon.objects.filter(code=code).prefetch_related(
        'products', 'categories', 'users').first()

    if not coupon:
        return 400, {'error': 'Invalid coupon code'}

    if not coupon.is_active:
        return 400, {'error': 'Coupon is not active'}

    if not (coupon.start_date <= now <= (coupon.end_date or now)):
        return 400, {'error': 'Coupon expired or not valid yet'}

    if coupon.max_usage and coupon.usage_count >= coupon.max_usage:
        return 400, {'error': 'Coupon usage limit reached'}

    cart = Cart.objects.filter(user=user).prefetch_related(
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
    ).first()

    if not cart.items.exists():
        return 400, {'error': 'Cart is empty'}

    for item in cart.items.all():
        if getattr(item.product, 'active_flash_sales', None):
            if len(item.product.active_flash_sales) > 0:
                return 400, {'error': 'Coupon cannot be used with flash sale products in the cart'}

    cart_amount = cart.items.aggregate(total_amount=Sum(
        F('quantity') * F('product__price')))['total_amount']

    if cart_amount < coupon.min_order_amount:
        return 400, {'error': 'Cart amount less than minimum amount required for this coupon'}

    cart_product_ids = set(
        cart.items.all().values_list('product__id', flat=True))

    if coupon.products.exists():
        coupon_product_ids = set(
            coupon.products.all().values_list('id', flat=True))
        if not cart_product_ids.issubset(coupon_product_ids):
            return 400, {'error': 'Coupon does not apply to products in the order'}

    if coupon.categories.exists():
        coupon_category_ids = set(
            coupon.categories.all().values_list('category__id', flat=True))
        product_category_ids = set(cart.items.all().values_list(
            'product__category__id', flat=True))
        if not product_category_ids.issubset(coupon_category_ids):
            return 400, {'error': 'Coupon does not apply to categories of products in the order'}

    if coupon.users.exists():
        coupon_user_ids = set(
            coupon.users.all().values_list('user__id', flat=True))
        if user.id not in coupon_user_ids:
            return 400, {'error': 'Coupon does not apply to this user'}

    discount_type = coupon.discount_type
    discount_value = coupon.discount_value
    if discount_type == 'percent':
        final_amount = cart_amount - (cart_amount * (discount_value / 100))
    elif discount_type == 'fixed':
        final_amount = cart_amount - discount_value

    response_data = {
        'status': 'Coupon is valid',
        'cart_amount': cart_amount,
        'coupon_type': discount_type,
        'coupon_value': discount_value,
        'coupon_code': code,
        'final_amount': int(final_amount),
    }

    if system:
        response_data['cart'] = cart

    return 200, response_data
