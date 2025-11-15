from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter

admin_router = DefaultRouter()
admin_router.register(
    r'category', views.AdminCategoryMangement, basename='admin-category')

admin_router.register(
    r'products', views.AdminProductMangement, basename='admin-product')
admin_router.register(
    r'product/image', views.AdminProductImageMangement, basename='admin-product-image')
admin_router.register(r'product/attribute',
                      views.AdminProductAttributeMangement, basename='admin-product-attribute')

admin_router.register(
    r'coupons', views.AdminCouponMangement, basename='admin-coupon')
admin_router.register(
    r'coupon/category', views.AdminCategoryCouponMangement, basename='admin-category-coupon')
admin_router.register(
    r'coupon/product', views.AdminProductCouponMangement, basename='admin-product-coupon')
admin_router.register(
    r'coupon/user', views.AdminUserCouponMangement, basename='admin-user-coupon')

admin_router.register(r'review', views.AdminReviewCreate,
                      basename='admin-review')

admin_router.register(
    r'cart/items', views.AdminCartItemCreate, basename='admin-cart-item')

admin_router.register(r'orders', views.AdminOrderView, basename='admin-order')

admin_router.register(r'payments', views.AdminPaymentView,
                      basename='admin-payment')

urlpatterns = [
    path('admin/', include(admin_router.urls),),

    path('category/', views.CategoryList.as_view(), name='category-list'),

    path('products/', views.ProductList.as_view(), name='product-list'),
    path('products/<slug:slug>/',
         views.ProductDetail.as_view(), name='product-detail'),

    path('coupon/', views.CoupenVerify.as_view(), name='coupon-verify'),

    path('review/', views.ReviewCreate.as_view(), name='review-create'),
    path('review/<int:pk>/', views.ReviewUpdate.as_view(), name='review-update'),
    path('review/image/', views.ReviweImageCreate.as_view(), name='review-image'),

    path('cart/', views.UserCartList.as_view(), name='user-cart-list'),
    path('cart/item/', views.UserCartItemCreate.as_view(),
         name='user-cart-item-create'),
    path('cart/item/<int:pk>/', views.UserCartItemDetail.as_view(),
         name='cart-item-detail'),

    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/create/', views.CreateOrderView.as_view(), name='order-create'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),

    path('payments/', views.PaymentListView.as_view(), name='payment-list'),

    path('flash_sale/', views.FlashSaleView.as_view(), name='flash-sale'),
]
