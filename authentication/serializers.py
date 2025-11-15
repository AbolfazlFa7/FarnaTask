from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .utils.validators import CustomPasswordValidator
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .utils.validators import normalize_email, normalize_phone


User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['email'] = self.user.email
        return data


class UsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'first_name', 'last_name',
                  'email', 'password', 'is_active', 'id')
        read_only_fields = ['is_active']
        write_only_fields = ['password']
        extra_kwargs = {
            'url': {
                'view_name': 'user',
                'lookup_field': 'pk'
            },
            'first_name': {
                'style': {'placeholder': 'Not Required'},
                'help_text': 'First Name'
            },
            'last_name': {
                'style': {'placeholder': 'Not Required'},
                'help_text': 'Last Name'
            },
            'password': {
                'min_length': 8,
                'max_length': 20,
                'help_text': 'Password',
                'style': {'input_type': 'password', 'placeholder': 'Password'}
            },
            'email': {
                'style': {'placeholder': 'Email'},
                'help_text': 'Email'
            },
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            **validated_data, validator_in_lower_layer=True)
        return user

    def validate_password(self, value):
        """
        I have created custom password validator, and added to AUTH_PASSWORD_VALIDATORS, but it not work when u passing it from serializer, becuase of this, we need manually validate it in serializer
        """

        CustomPasswordValidator.validate(self=None, password=value)
        return value


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'phone', 'first_name',
                  'last_name', 'is_active', 'birthday', 'gender']
        read_only_fields = ['is_active', 'email', 'phone']
        extra_kwargs = {
            'email': {
                'style': {'placeholder': 'Email'},
                'help_text': 'Email'
            },
            'phone': {
                'style': {'placeholder': 'Phone'},
                'help_text': 'Phone'
            },
            'first_name': {
                'style': {'placeholder': 'First Name'},
                'help_text': 'First Name'
            },
            'last_name': {
                'style': {'placeholder': 'Last Name'},
                'help_text': 'Last Name'
            },
        }


class LogoutSerializers(serializers.Serializer):
    refresh = serializers.CharField(
        style={'input_type': 'hidden'}, help_text='refresh token')


class SendOTPActivateAccountSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, email):
        email = normalize_email(email)
        return email


class VerifyOTPActivateAccountSerializer(SendOTPActivateAccountSerializer):
    code = serializers.IntegerField(required=True, help_text='Code')

    def validate_code(self, code):
        """check code length and code must be positive integer"""

        if len(str(code)) != 6 or code < 0:
            raise ValidationError(
                {'status': 'Code must be positive integer, and length must be 6'})
        else:
            return str(code)


class SendOTPPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, email):
        email = normalize_email(email)
        return email


class VerifyOTPPasswordResetSerializer(SendOTPPasswordResetSerializer, VerifyOTPActivateAccountSerializer):
    password = serializers.CharField(required=True, help_text='Password')
    confirm_password = serializers.CharField(
        required=True, help_text='Confirm Password')

    def validate(self, attrs):
        password = attrs.get('password')
        confirm_password = attrs.get('confirm_password')
        if password != confirm_password:
            raise serializers.ValidationError(
                {"password": "Password and Confirm Password must be same", "confirm_password": "Password and Confirm Password must be same"})
        user = self.context.get('user')
        validate_password(password, user)
        return attrs


class SendOTPPhoneSetSerializer(serializers.Serializer):
    phone = serializers.CharField(required=True)

    def validate_phone(self, phone):
        phone = normalize_phone(phone)
        return phone


class VerifyOTPPhoneSetSerializer(SendOTPPhoneSetSerializer, VerifyOTPActivateAccountSerializer):
    pass
