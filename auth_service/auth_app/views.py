from django.conf import settings
from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from django.utils import timezone
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import (
    ForgotPasswordConfirmSerializer,
    ForgotPasswordRequestSerializer,
    LoginSerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
    RegisterWithOtpSerializer,
    RequestOtpSerializer,
    TrainerProfileSerializer,
)
from .tasks import send_otp_email_task
from .tokens import get_token_pair
from .utils.otp import (
    can_request_otp,
    delete_otp,
    generate_otp,
    get_failed_attempts,
    record_failed_attempt,
    reset_failed_attempts,
    store_otp,
    verify_otp,
)
from .utils.rabbit_producer import publish_trainer_registered, publish_user_created


class RequestOtpView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RequestOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        if not can_request_otp(email, "register"):
            return Response(
                {"detail": "OTP requested too recently. Try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        otp = generate_otp()
        store_otp(email, otp, "register")
        send_otp_email_task.delay(email, otp, "register")

        return Response({"detail": "OTP sent to email."}, status=status.HTTP_200_OK)


class UserRegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterWithOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        email = data["email"]
        otp = data["otp"]

        # rate limit check
        if get_failed_attempts(email, "register") >= getattr(
            settings, "OTP_MAX_FAILED_ATTEMPTS", 5
        ):
            return Response(
                {"detail": "Too many failed attempts."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not verify_otp(email, otp, "register"):
            record_failed_attempt(email, "register")
            return Response(
                {"detail": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # OTP ok — reset attempts (defense in depth)
        reset_failed_attempts(email, "register")

        password = data.pop("password")

        try:
            with transaction.atomic():
                # create user explicitly, don't trust client-supplied role
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    name=data.get("name"),
                    phone=data.get("phone"),
                    role=User.ROLE_USER,
                )
                user.is_verified = True
                user.save(update_fields=["is_verified"])

                transaction.on_commit(lambda: publish_user_created(user.id, user.email))
        except IntegrityError:
            # email uniqueness race handled gracefully
            return Response(
                {"email": "Email is already registered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
            },
            status=status.HTTP_201_CREATED,
        )


class TrainerRegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterWithOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        email = data["email"]
        otp = data["otp"]

        if get_failed_attempts(email, "register") >= getattr(
            settings, "OTP_MAX_FAILED_ATTEMPTS", 5
        ):
            return Response(
                {"detail": "Too many failed attempts."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not verify_otp(email, otp, "register"):
            record_failed_attempt(email, "register")
            return Response(
                {"detail": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reset_failed_attempts(email, "register")

        password = data.pop("password")

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    name=data.get("name"),
                    phone=data.get("phone"),
                    role=User.ROLE_TRAINER,
                    is_approved=False,
                )
                user.is_verified = True
                user.save(
                    update_fields=["is_verified"]
                )  # is_approved already set on create

                transaction.on_commit(
                    lambda: publish_trainer_registered(user.id, user.email)
                )
        except IntegrityError:
            return Response(
                {"email": "Email is already registered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "is_approved": user.is_approved,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        password = serializer.validated_data["password"]

        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response(
                {"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {"detail": "User is inactive."}, status=status.HTTP_403_FORBIDDEN
            )

        # create tokens
        tokens = get_token_pair(user)
        return Response(
            {
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "role": user.role,
                    "is_verified": user.is_verified,
                },
            },
            status=status.HTTP_200_OK,
        )


class ProfileView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TrainerProfileView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = TrainerProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        google_token = request.data.get("id_token")
        if not google_token:
            return Response(
                {"detail": "id_token is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Verify token with Google
        try:
            payload = id_token.verify_oauth2_token(
                google_token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )
        except ValueError:
            return Response(
                {"detail": "Invalid Google token"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as exc:
            return Response(
                {"detail": "Token verification failed", "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sub = payload.get("sub")
        email = payload.get("email")
        email_verified = payload.get("email_verified", False)
        name = payload.get("name") or ""
        picture = payload.get("picture")

        if not email:
            return Response(
                {"detail": "Google account has no email"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not email_verified:
            return Response(
                {"detail": "Google email not verified"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = False
        linked = False
        user = None

        with transaction.atomic():
            try:
                user = User.objects.get(oauth_provider="google", oauth_uid=sub)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(email__iexact=email.lower())

                    if user.oauth_provider and user.oauth_provider != "google":
                        return Response({...}, status=409)

                    if (
                        user.oauth_uid != sub
                        or user.oauth_provider != "google"
                        or not user.is_verified
                    ):
                        user.oauth_provider = "google"
                        user.oauth_uid = sub
                        user.is_verified = True
                        if not getattr(user, "name", None):
                            user.name = name
                        user.save(
                            update_fields=[
                                "oauth_provider",
                                "oauth_uid",
                                "is_verified",
                                "name",
                            ]
                        )
                        linked = True

                except User.DoesNotExist:
                    user = User.objects.create(
                        email=email.lower(),
                        name=name,
                        oauth_provider="google",
                        oauth_uid=sub,
                        is_verified=True,
                    )
                    try:
                        user.set_unusable_password()
                        user.save(update_fields=["password"])
                    except Exception:
                        user.save()
                    created = True

            if created:
                uid = str(user.id)
                uemail = user.email
                transaction.on_commit(
                    lambda uid=uid, email=uemail: publish_user_created(uid, email)
                )

        # ISSUE TOKENS USING THE HELPER (this replaces RefreshToken.for_user)
        tokens = get_token_pair(user)

        try:
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])
        except Exception:
            pass

        return Response(
            {
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": getattr(user, "name", None),
                    "role": getattr(user, "role", None),
                    "oauth_provider": getattr(user, "oauth_provider", None),
                },
                "created": created,
                "linked": linked,
            },
            status=status.HTTP_200_OK,
        )


class ProfileEditView(generics.RetrieveUpdateAPIView):
    http_method_names = ["get", "patch", "put", "head", "options"]
    serializer_class = ProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ForgotPasswordRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        # Rate limit check
        if not can_request_otp(email, purpose="password_reset"):
            return Response(
                {"detail": "Too many requests. Try again later."}, status=429
            )

        otp = generate_otp()

        try:
            store_otp(email, otp, purpose="password_reset")
        except Exception:
            return Response({"detail": "Could not store OTP."}, status=500)

        # Send OTP via Celery
        try:
            send_otp_email_task.delay(email, otp, "password_reset")
        except Exception:
            delete_otp(email, purpose="password_reset")
            return Response({"detail": "Could not send OTP."}, status=500)

        return Response({"detail": "OTP sent to email."})


class ForgotPasswordConfirmView(APIView):

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        otp = serializer.validated_data["otp"]
        new_password = serializer.validated_data["new_password"]

        # ensure user exists
        user = User.objects.filter(email=email).first()
        if not user:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_400_BAD_REQUEST
            )

        # optional: enforce max failed attempts
        max_failed = getattr(settings, "OTP_MAX_FAILED_ATTEMPTS", None)
        if max_failed is not None:
            try:
                failed = get_failed_attempts(email, purpose="password_reset")
            except Exception:
                return Response(
                    {"detail": "Internal error"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            if failed >= max_failed:
                return Response(
                    {"detail": "Too many failed attempts. Request a new OTP."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # verify otp using redis-backed util. verify_otp deletes OTP on success and increments failures on bad attempts.
        try:
            ok = verify_otp(email, otp, purpose="password_reset")
        except Exception:
            return Response(
                {"detail": "Internal error verifying OTP."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not ok:
            return Response(
                {"detail": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # OTP valid: set new password
        user.set_password(new_password)
        if hasattr(user, "password_changed_at"):
            user.password_changed_at = timezone.now()
            user.save(update_fields=["password", "password_changed_at"])
        else:
            user.save(update_fields=["password"])

        # cleanup: ensure OTP removed (verify_otp deletes it on success, but do a best-effort delete)
        try:
            delete_otp(email, purpose="password_reset")
        except Exception:
            pass

        return Response(
            {
                "detail": "Password reset successful. You may now log in with the new password."
            },
            status=status.HTTP_200_OK,
        )


from .models import RefreshTokenRecord


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"detail": "Refresh token is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            token = RefreshToken(refresh_token)
            token.blacklist()
            jti = token["jti"]
            RefreshTokenRecord.objects.filter(jti=jti).update(revoked=True)

            return Response(
                {"detail": "Logged out successfully"},
                status=status.HTTP_205_RESET_CONTENT,
            )

        except Exception:
            return Response(
                {"detail": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST
            )
