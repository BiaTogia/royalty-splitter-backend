from rest_framework import serializers
from backend.models import UserAccount, Role
from api.validators import FileValidator
from api.sanitizers import InputSanitizer
from django.core.exceptions import ValidationError


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'role_name']


class UserAccountSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    profile_image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserAccount
        fields = ['id', 'name', 'email', 'role', 'country', 'profile_image', 'profile_image_url']
        read_only_fields = ['id', 'role', 'profile_image_url']

    def validate_name(self, value):
        """Sanitize and validate name"""
        if not value:
            raise serializers.ValidationError("Name cannot be empty")
        clean_name = InputSanitizer.sanitize_text(value, max_length=100)
        if len(clean_name.strip()) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters")
        return clean_name
    
    def validate_email(self, value):
        """Sanitize and validate email"""
        try:
            return InputSanitizer.sanitize_email(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
    
    def validate_country(self, value):
        """Sanitize country name"""
        if value:
            return InputSanitizer.sanitize_text(value, max_length=50)
        return value

    def validate_profile_image(self, value):
        """Validate image file - size and type"""
        if value:
            try:
                FileValidator.validate_image(value)
            except ValidationError as e:
                raise serializers.ValidationError(str(e))
        return value

    def get_profile_image_url(self, obj):
        request = self.context.get('request')
        if getattr(obj, 'profile_image', None):
            try:
                url = obj.profile_image.url
                if request is not None:
                    return request.build_absolute_uri(url)
                return url
            except Exception:
                return None
        return None


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    country = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = UserAccount
        fields = ['id', 'name', 'email', 'password', 'country']
        extra_kwargs = {
            'name': {'required': True},
            'email': {'required': True},
        }

    def validate_email(self, value):
        if UserAccount.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Name cannot be empty.")
        return value
    
    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        return value

    def create(self, validated_data):
        user = UserAccount.objects.create_user(
            email=validated_data['email'],
            name=validated_data['name'],
            password=validated_data['password'],
            country=validated_data.get('country', '')
        )
        return user
