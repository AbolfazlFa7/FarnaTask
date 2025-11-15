from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.contrib import messages

from taggit.admin import TagAdmin

from .models import (
    Category, Product, ProductImage, ProductAttribute, Coupon, ProductCoupon,
    CategoryCoupon, UserCoupon, Review, ReviewImage, Cart, CartItem,
    Order, OrderItem, Payment, FlashSale, FlashSaleProduct
)


# -------------------------
# Inlines
# -------------------------
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ('image_preview',)
    fields = ('image', 'is_feature', 'image_preview')
    ordering = ('-is_feature',)

    def image_preview(self, obj):
        if obj and obj.image:
            return format_html('<img src="{}" style="max-height:100px;"/>', obj.image.url)
        return ""
    image_preview.short_description = _('Preview')


class ProductAttributeInline(admin.TabularInline):
    model = ProductAttribute
    extra = 1
    fields = ('key', 'value')


class ProductCouponInline(admin.TabularInline):
    model = ProductCoupon
    extra = 0
    autocomplete_fields = ('coupon',)


class FlashSaleProductInline(admin.TabularInline):
    model = FlashSaleProduct
    extra = 0
    autocomplete_fields = ('product',)
    fields = ('product', 'discount_type', 'discount_value', 'limited_stock')


class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 0
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj and obj.image:
            return format_html('<img src="{}" style="max-height:80px;"/>', obj.image.url)
        return ""
    image_preview.short_description = _('Preview')


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    fields = ('user', 'rating', 'title', 'created_at')
    readonly_fields = ('user', 'rating', 'title', 'comment',
                       'created_at', 'updated_at')
    show_change_link = True


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ('product',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_link', 'quantity', 'price')
    fields = ('product_link', 'quantity', 'price')

    def product_link(self, obj):
        if obj.product:
            url = reverse('admin:%s_%s_change' % (obj.product._meta.app_label, obj.product._meta.model_name),
                          args=(obj.product.pk,))
            return format_html('<a href="{}">{}</a>', url, obj.product)
        return "-"
    product_link.short_description = _('Product')


# -------------------------
# Admin actions
# -------------------------
def make_available(modeladmin, request, queryset):
    updated = queryset.update(is_available=True)
    modeladmin.message_user(request, _(
        '%d products marked as available.') % updated, messages.SUCCESS)


make_available.short_description = _('Mark selected products as available')


def make_unavailable(modeladmin, request, queryset):
    updated = queryset.update(is_available=False)
    modeladmin.message_user(request, _(
        '%d products marked as unavailable.') % updated, messages.SUCCESS)


make_unavailable.short_description = _('Mark selected products as unavailable')


def generate_coupon_codes(modeladmin, request, queryset):
    created = 0
    for obj in queryset:
        if not obj.code:
            obj.code = obj.generate_coupon_code()
            obj.save()
            created += 1
    modeladmin.message_user(request, _(
        '%d coupon codes generated.') % created, messages.SUCCESS)


generate_coupon_codes.short_description = _(
    'Generate codes for selected coupons')


# -------------------------
# ModelAdmins
# -------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'is_active')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)


@admin.register(Product)
class ProductAdmin(TagAdmin, admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'price', 'stock',
                    'is_available', 'created_at', 'get_final_price_display')
    list_filter = ('is_available', 'category', 'tags')
    search_fields = ('name', 'sku', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = (ProductImageInline, ProductAttributeInline,
               ProductCouponInline, )
    actions = (make_available, make_unavailable)
    autocomplete_fields = ('category',)
    list_select_related = ('category',)

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'sku', 'category', 'description', 'tags')
        }),
        (_('Inventory & Pricing'), {
            'fields': ('price', 'stock', 'is_available', 'get_final_price_display')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def get_final_price_display(self, obj):
        try:
            price = obj.get_final_price()
        except Exception:
            price = obj.price
        return f"{price}"
    get_final_price_display.short_description = _('Final Price (current sale)')

    # show SKU generation hint
    def save_model(self, request, obj, form, change):
        # sku is auto-generated in model.save() if missing, so just save normally
        super().save_model(request, obj, form, change)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image', 'is_feature',)
    list_filter = ('is_feature', 'product')
    search_fields = ('product__name',)
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj and obj.image:
            return format_html('<img src="{}" style="max-height:120px;"/>', obj.image.url)
        return ""
    image_preview.short_description = _('Preview')


@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ('product', 'key', 'value')
    search_fields = ('product__name', 'key', 'value')
    autocomplete_fields = ('product',)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value',
                    'is_active', 'start_date', 'end_date', 'usage_count')
    list_filter = ('is_active', 'discount_type',)
    search_fields = ('code',)
    readonly_fields = ('usage_count',)
    actions = (generate_coupon_codes,)
    fieldsets = (
        (None, {
            'fields': ('code', 'description', 'discount_type', 'discount_value', 'is_active')
        }),
        (_('Usage & Validity'), {
            'fields': ('start_date', 'end_date', 'min_order_amount', 'max_usage', 'usage_count')
        }),
    )

    def save_model(self, request, obj, form, change):
        # validate percent bounds
        obj.full_clean()
        super().save_model(request, obj, form, change)


@admin.register(ProductCoupon)
class ProductCouponAdmin(admin.ModelAdmin):
    list_display = ('product', 'coupon')
    search_fields = ('product__name', 'coupon__code')
    autocomplete_fields = ('product', 'coupon')


@admin.register(CategoryCoupon)
class CategoryCouponAdmin(admin.ModelAdmin):
    list_display = ('category', 'coupon')
    search_fields = ('category__name', 'coupon__code')
    autocomplete_fields = ('category', 'coupon')


@admin.register(UserCoupon)
class UserCouponAdmin(admin.ModelAdmin):
    list_display = ('user', 'coupon')
    search_fields = ('user__email', 'coupon__code')
    autocomplete_fields = ('user', 'coupon')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'title', 'created_at')
    list_filter = ('rating',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = (ReviewImageInline,)
    search_fields = ('product__name', 'user__email', 'title', 'comment')
    autocomplete_fields = ('product', 'user')


@admin.register(ReviewImage)
class ReviewImageAdmin(admin.ModelAdmin):
    list_display = ('review', 'image')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj and obj.image:
            return format_html('<img src="{}" style="max-height:100px;"/>', obj.image.url)
        return ""
    image_preview.short_description = _('Preview')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'updated_at')
    readonly_fields = ('updated_at',)
    inlines = (CartItemInline,)
    search_fields = ('user__email',)
    autocomplete_fields = ('user',)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity')
    search_fields = ('cart__id', 'product__name')
    autocomplete_fields = ('cart', 'product')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'tracking_code', 'status',
                    'total_amount', 'discount_amount', 'final_amount', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('tracking_code', 'user__email')
    readonly_fields = ('tracking_code', 'created_at', 'updated_at')
    inlines = (OrderItemInline,)

    actions = ['mark_as_paid', 'mark_as_shipped',
               'mark_as_completed', 'mark_as_canceled']

    def mark_as_paid(self, request, queryset):
        updated = queryset.update(status='paid')
        self.message_user(request, _('%d orders marked as paid.') %
                          updated, messages.SUCCESS)
    mark_as_paid.short_description = _('Mark selected orders as paid')

    def mark_as_shipped(self, request, queryset):
        updated = queryset.update(status='shipped')
        self.message_user(request, _('%d orders marked as shipped.') %
                          updated, messages.SUCCESS)
    mark_as_shipped.short_description = _('Mark selected orders as shipped')

    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, _(
            '%d orders marked as completed.') % updated, messages.SUCCESS)
    mark_as_completed.short_description = _(
        'Mark selected orders as completed')

    def mark_as_canceled(self, request, queryset):
        updated = queryset.update(status='canceled')
        self.message_user(request, _(
            '%d orders marked as canceled.') % updated, messages.SUCCESS)
    mark_as_canceled.short_description = _('Mark selected orders as canceled')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price')
    search_fields = ('order__tracking_code', 'product__name')
    readonly_fields = ('price',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'amount', 'method', 'status',
                    'transaction_id', 'tracking_code', 'created_at')
    list_filter = ('status', 'method', 'created_at')
    search_fields = ('tracking_code', 'transaction_id', 'order__tracking_code')
    readonly_fields = ('tracking_code', 'created_at')

    actions = ['mark_success', 'mark_failed']

    def mark_success(self, request, queryset):
        updated = queryset.update(status='success')
        self.message_user(request, _(
            '%d payments marked as success.') % updated, messages.SUCCESS)
    mark_success.short_description = _('Mark selected payments as success')

    def mark_failed(self, request, queryset):
        updated = queryset.update(status='failed')
        self.message_user(request, _(
            '%d payments marked as failed.') % updated, messages.SUCCESS)
    mark_failed.short_description = _('Mark selected payments as failed')


@admin.register(FlashSale)
class FlashSaleAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_time', 'end_time', 'is_running')
    list_filter = ('start_time', 'end_time')
    inlines = (FlashSaleProductInline,)
    search_fields = ('title',)

    def is_running(self, obj):
        return obj.is_running()
    is_running.boolean = True
    is_running.short_description = _('Running')


@admin.register(FlashSaleProduct)
class FlashSaleProductAdmin(admin.ModelAdmin):
    list_display = ('flash_sale', 'product', 'discount_type',
                    'discount_value', 'limited_stock')
    list_filter = ('discount_type', 'flash_sale')
    search_fields = ('product__name', 'flash_sale__title')
    autocomplete_fields = ('product', 'flash_sale')
