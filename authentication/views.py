from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import generics
from rest_framework import permissions
from rest_framework import status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from . import serializers
from .permissions import IsOwnerOrAdmin, IsAnonymous
from .utils.otp_service import OTPService

User = get_user_model()


class TokenObtainPairView(TokenObtainPairView):
    """I have added this feature just for showing 'email' field beside 'access' & 'refresh' token"""

    serializer_class = serializers.CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class UsersApiView(generics.ListCreateAPIView):
    """
    - Get request: See all users (admin only)
    - Post request: Create new user
    """

    queryset = User.objects.all()
    serializer_class = serializers.UsersSerializer
    lookup_field = 'pk'

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAnonymous()]
        elif self.request.method == 'GET':
            return [permissions.IsAdminUser()]
        else:
            return [permissions.IsAdminUser()]


class UserApiView(generics.RetrieveUpdateDestroyAPIView):
    """
    Show user detail by id
    - Get request: See user detail (owner or admin)
    - Put or Patch request: Update user details, except few fields (owner or admin)
    - Delete request: Delete user (owner or admin)
    """

    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer
    permission_classes = [IsOwnerOrAdmin]


class UserMeApiView(generics.RetrieveUpdateDestroyAPIView):
    """
    Show user detail by current user
    - Get request: See user detail (owner or admin)
    - Put or Patch request: Update user details, except few fields (owner or admin)
    - Delete request: Delete user (owner or admin)
    """

    serializer_class = serializers.UserSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_object(self):
        user = self.request.user
        return user


class LogoutApiView(generics.GenericAPIView):
    """blacklist refresh token"""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.LogoutSerializers

    @extend_schema(
        description='It get refresh token of user and blacklist it',
        summary='Logout User',
        responses={
            200: OpenApiResponse(
                response=dict,
                description="Successfully logged out",
                examples=[
                    OpenApiExample(
                        name="Success Response",
                        value={
                            "status": "You have logged out"
                        },
                        status_codes=[200]
                    )
                ]
            ),
            400: OpenApiResponse(
                response=dict,
                description="Token is Invalid",
                examples=[
                    OpenApiExample(
                        name="Success Response",
                        value={
                            "status": "Token is Invalid"
                        },
                        status_codes=[400]
                    )
                ]
            ),
            403: OpenApiResponse(
                response=dict,
                description="User must be logged in",
                examples=[
                    OpenApiExample(
                        name="Success Response",
                        value={
                            "status": "You are not logged in"
                        },
                        status_codes=[403]
                    )
                ]
            )
        }
    )
    def post(self, request):
        refresh_token = request.data.get('refresh')
        try:
            refresh_token = RefreshToken(refresh_token)
            refresh_token.blacklist()
            response = {'status': 'You have logged out'}
            status_code = status.HTTP_200_OK
        except Exception as e:
            response = {'status': 'Token is Invalid'}
            status_code = status.HTTP_400_BAD_REQUEST

        return Response(response, status=status_code)


class SendOTPActivateAccountApiView(generics.GenericAPIView):
    serializer_class = serializers.SendOTPActivateAccountSerializer

    @extend_schema(
        description='Send OTP to user email for activate account',
        summary='Send Activate Account OTP',
        responses={
            200: OpenApiResponse(
                response=dict,
                description="Successfully OTP has been sent to user email",
                examples=[
                    OpenApiExample(
                        name="Success Response",
                        value={
                            'status': 'Veryfication Code has been sent to user email'
                        },
                    )
                ]
            ),
            400: OpenApiResponse(
                response=dict,
                description="OTP has not been sent to user",
                examples=[
                    OpenApiExample(
                        name="User Already Activated",
                        value={
                            'status': 'User Already Activated',
                        }
                    ),
                    OpenApiExample(
                        name="Code not expired yet",
                        value={
                            'status': 'Code already has been sented',
                        }
                    ),
                    OpenApiExample(
                        name="User Not Exists",
                        value={
                            'status': 'User Not Exists',
                        }
                    )
                ]
            )
        }
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = request.data.get('email')
        response_data, status_code = OTPService.send_otp_activate_account(
            email)
        return Response(response_data, status=status_code)


class VerifyOTPActivateAccountApiView(generics.GenericAPIView):
    serializer_class = serializers.VerifyOTPActivateAccountSerializer

    @extend_schema(
        description='Verify OTP code sent to user email for activate account',
        summary='Verify OTP for activate account',
        request=serializers.VerifyOTPActivateAccountSerializer,
        responses={
            200: OpenApiResponse(
                response=dict,
                description="User successfully verified",
                examples=[
                    OpenApiExample(
                        name="Success Response",
                        value={
                            "status": "User has Verified"
                        },
                        status_codes=[200]
                    )
                ]
            ),
            400: OpenApiResponse(
                response=dict,
                description="Error in OTP verification",
                examples=[
                    OpenApiExample(
                        name="User Already Verified",
                        value={
                            "status": "User has Verified already"
                        }
                    ),
                    OpenApiExample(
                        name="Invalid Code",
                        value={
                            "status": "Invalid Code"
                        }
                    ),
                    OpenApiExample(
                        name="Too Many Attempts",
                        value={
                            "status": "Too many attempts"
                        }
                    ),
                    OpenApiExample(
                        name="Invalid User",
                        value={
                            "status": "Invalid User"
                        }
                    ),
                ]
            ),
        }
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = request.data.get('email')
        code = request.data.get('code')
        response_data, status_code = OTPService.verify_otp_activate_account(
            email, code)
        return Response(response_data, status=status_code)


class SendOTPPasswordResetView(generics.GenericAPIView):
    serializer_class = serializers.SendOTPPasswordResetSerializer
    permission_classes = [IsAnonymous]

    @extend_schema(
        description='Send OTP code to user email for password reset',
        summary='Send OTP for password reset',
        request=serializers.SendOTPPasswordResetSerializer,
        responses={
            200: OpenApiResponse(
                response=dict,
                description="OTP sent successfully",
                examples=[
                    OpenApiExample(
                        name="Success Response",
                        value={
                            "status": "Veryfication Code has been sent to user email"
                        },
                        status_codes=[200]
                    )
                ]
            ),
            400: OpenApiResponse(
                response=dict,
                description="Error in sending OTP",
                examples=[
                    OpenApiExample(
                        name="Code has not expired yet",
                        value={
                            "status": "Code already has been sented"
                        }
                    ),
                    OpenApiExample(
                        name="Invalid User",
                        value={
                            "status": "Invalid User"
                        }
                    ),
                    OpenApiExample(
                        name="User Not Active",
                        value={
                            "status": "User is not active"
                        }
                    ),
                ]
            ),
        }
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = request.data.get('email')
        response_data, status_code = OTPService.send_otp_reset_password(
            email)
        return Response(response_data, status=status_code)


class VerifyOTPPasswordResetView(generics.GenericAPIView):
    serializer_class = serializers.VerifyOTPPasswordResetSerializer
    permission_classes = [IsAnonymous]

    @extend_schema(
        description='Verify OTP code and reset password for user',
        summary='Verify OTP and Reset Password',
        request=serializers.VerifyOTPPasswordResetSerializer,
        responses={
            200: OpenApiResponse(
                response=dict,
                description="Password reset successfully",
                examples=[
                    OpenApiExample(
                        name="Success Response",
                        value={
                            "status": "Password has been reset"
                        },
                        status_codes=[200]
                    )
                ]
            ),
            400: OpenApiResponse(
                response=dict,
                description="Error in OTP verification or password reset",
                examples=[
                    OpenApiExample(
                        name="Too Many Attempts",
                        value={
                            "status": "Too many attempts"
                        }
                    ),
                    OpenApiExample(
                        name="Invalid User",
                        value={
                            "status": "Invalid User"
                        }
                    ),
                    OpenApiExample(
                        name="Invalid Code",
                        value={
                            "status": "Invalid Code"
                        }
                    ),
                ]
            ),
        }
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = request.data.get('email')
        code = request.data.get('code')
        password = request.data.get('password')

        response_data, status_code = OTPService.verify_otp_reset_password(
            email, code, password)

        return Response(response_data, status=status_code)


class SendOTPPhoneSetApiView(generics.GenericAPIView):
    serializer_class = serializers.SendOTPPhoneSetSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        description='Send OTP code to User Phone Number for Set phone number',
        summary='Send OTP for set phone number',
        request=serializers.SendOTPPhoneSetSerializer,
        responses={
            200: OpenApiResponse(
                response=dict,
                description="OTP sent successfully",
                examples=[
                    OpenApiExample(
                        name="Success Response",
                        value={
                            "status": "Veryfication Code has been sent to user email"
                        },
                        status_codes=[200]
                    )
                ]
            ),
            400: OpenApiResponse(
                response=dict,
                description="Error in sending OTP to phone",
                examples=[
                    OpenApiExample(
                        name="Code Already Sent",
                        value={
                            "status": "Code already has been sented"
                        }
                    ),
                    OpenApiExample(
                        name="Phone Number Cannot be Changed",
                        value={
                            "status": "User Phone Number Cannot be changed"
                        }
                    ),
                    OpenApiExample(
                        name="User Not Active",
                        value={
                            "status": "User Must be active first"
                        }
                    ),
                ]
            ),
        }
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = request.data.get('phone')
        user = request.user
        response_data, status_code = OTPService.send_otp_phone_set(user, phone)
        return Response(response_data, status=status_code)


class VerifyOTPPhoneSetApiView(generics.GenericAPIView):
    serializer_class = serializers.VerifyOTPPhoneSetSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        description='Verify OTP Code That has been sent to user phone for Set phone number',
        summary='Verify OTP and Set Phone Number',
        request=serializers.VerifyOTPPhoneSetSerializer,
        responses={
            200: OpenApiResponse(
                response=dict,
                description="Phone number changed successfully",
                examples=[
                    OpenApiExample(
                        name="Success Response",
                        value={
                            "status": "Phone has been changed"
                        },
                        status_codes=[200]
                    )
                ]
            ),
            400: OpenApiResponse(
                response=dict,
                description="Error in OTP verification or phone change",
                examples=[
                    OpenApiExample(
                        name="Too Many Attempts",
                        value={
                            "status": "Too many attempts"
                        }
                    ),
                    OpenApiExample(
                        name="Invalid Code",
                        value={
                            "status": "Invalid Code"
                        }
                    ),
                ]
            ),
        }
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = request.data.get('phone')
        code = request.data.get('code')
        user = request.user
        response_data, status_code = OTPService.verify_otp_phone_set(
            user, phone, code)
        return Response(response_data, status=status_code)
