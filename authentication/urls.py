from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.views import TokenVerifyView
from django.urls import path
from . import views

urlpatterns = [
    # JWT
    path('token/', views.TokenObtainPairView.as_view(), name='Token'),
    path('token/refresh/', TokenRefreshView.as_view(), name='Token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='Token_verify'),

    # User Management
    path('users/', views.UsersApiView.as_view(), name='users'),
    path('users/<int:pk>/', views.UserApiView.as_view(), name='user'),
    path('users/me/', views.UserMeApiView.as_view(), name='user_me'),
    path('logout/', views.LogoutApiView.as_view(), name='logout'),

    # OTP
    path('otp/send/activate_account/', views.SendOTPActivateAccountApiView.as_view(),
         name='send_otp_activate_account'),
    path('otp/verify/activate_account/', views.VerifyOTPActivateAccountApiView.as_view(),
         name='verify_otp_activate_account'),
    path('otp/send/reset_password/', views.SendOTPPasswordResetView.as_view(),
         name='send_otp_reset_password'),
    path('otp/verify/reset_password/', views.VerifyOTPPasswordResetView.as_view(),
         name='verify_otp_reset_password'),
    path('otp/send/phone_set/', views.SendOTPPhoneSetApiView.as_view(),
         name='send_otp_phone_set'),
    path('otp/verify/phone_set/', views.VerifyOTPPhoneSetApiView.as_view(),
         name='verify_otp_phone_set'),
]
