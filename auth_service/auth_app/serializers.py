from django.core.validators import RegexValidator
from django.utils import timezone
from rest_framework import serializers

from .models import User

password_validator = RegexValidator(
    regex=r"^.{8,}$", message="Password must be at least 8 characters long."
)

phone_validator = RegexValidator(
    regex=r"^\+?[0-9]{7,15}$",
    message="Enter phone number in format: +999999999. Up to 15 digits allowed.",
)


# 1) Register - create user (used by user and trainer register views)
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[password_validator])

    class Meta:
        model = User
        # role handled by view (trainer endpoint will set role and is_active)
        fields = ["id", "email", "password", "name", "phone", "role"]
        read_only_fields = ["id"]

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already registered.")
        return value

    def validate_phone(self, value):
        if value:
            phone_validator(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        # create_user will normalize again; if view wants to override role/is_active it should pass them in validated_data
        user = User.objects.create_user(password=password, **validated_data)
        return user


# 2) Login - simple credentials container used by login view
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email").strip().lower()
        password = attrs.get("password")

        from .models import User  # import inside to avoid circular import

        user = User.objects.filter(email=email).first()

        if user is None:
            raise serializers.ValidationError(
                {"email": "No account found with this email."}
            )

        # Trainer account inactive?
        if user.role == User.ROLE_TRAINER and user.is_active is False:
            raise serializers.ValidationError(
                {"detail": "Your trainer account is not yet approved by admin."}
            )

        # Credentials validation happens in LoginView using authenticate()
        # but we attach user for the view to use
        attrs["user"] = user
        return attrs


# 3) Profile (read) - show user profile data (no sensitive fields)
class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone",
            "name",
            "role",
            "oauth_provider",
            "date_joined",
            "is_active",
            "is_verified",
            "metadata",
        ]
        read_only_fields = fields


# 4) Profile update - fields the user may edit themself
class ProfileUpdateSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(
        required=False, allow_blank=True, validators=[phone_validator]
    )

    class Meta:
        model = User
        fields = ["name", "phone", "metadata"]

    def update(self, instance, validated_data):
        # update only provided fields
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save(update_fields=list(validated_data.keys()))
        return instance


# 6) Trainer Profile (read) - show trainer profile data along with user data
class TrainerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone",
            "name",
            "role",
            "date_joined",
            "is_active",
            "is_verified",
            "is_approved",
            "metadata",
        ]
        read_only_fields = fields


# 5) Password change - authenticated user changes their password
class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True, validators=[password_validator]
    )

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        new_pw = self.validated_data["new_password"]
        user.set_password(new_pw)
        user.password_changed_at = timezone.now()
        user.save(update_fields=["password", "password_changed_at"])
        return user


class RequestOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "This email is already registered. Use login or password reset instead."
            )
        return value


class VerifyOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()

    def validate_email(self, value):
        return value.strip().lower()


class RegisterWithOtpSerializer(RegisterSerializer):
    otp = serializers.CharField(write_only=True)

    class Meta(RegisterSerializer.Meta):
        fields = RegisterSerializer.Meta.fields + ["otp"]


class ForgotPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        value = value.strip().lower()
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No account found with this email.")
        return value


class ForgotPasswordConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True, validators=[password_validator]
    )

    def validate_email(self, value):
        return value.strip().lower()


class AdminTrainerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "is_active",
            "is_approved",
            "date_joined",
        ]


class AdminUserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "is_active",
            "date_joined",
        ]


class AdminUserStatusSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()
