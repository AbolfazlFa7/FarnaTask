from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView
from drf_spectacular.views import SpectacularRedocView
from drf_spectacular.views import SpectacularSwaggerView
import debug_toolbar
from product.views import PaymentVerifyView

urlpatterns = [
    path('admin/', admin.site.urls),

    path('__debug__/', include(debug_toolbar.urls)),

    # Schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(), name='redoc'),
    path('api/schema/ui/', SpectacularSwaggerView.as_view(), name='schema_ui'),

    # Authentication
    path('api/auth/', include('authentication.urls')),

    # Products
    path('api/p/', include('product.urls')),
    path('api/payment/callback/', PaymentVerifyView.as_view(), name='payment-verify'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
