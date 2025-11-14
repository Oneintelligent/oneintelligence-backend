import logging
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from rest_framework import status, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse

from .models import User
from .serializers import (
    UserSerializer,
    SignInSerializer,
    SignUpSerializer,
    SignOutSerializer,
)
from app.utils.response import api_response

logger = logging.getLogger(__name__)


# ============================================================
# USER VIEWSET (Authentication + Profile)
# ============================================================

@extend_schema_view(
    list=extend_schema(exclude=True),
    retrieve=extend_schema(exclude=True),
    update=extend_schema(exclude=True),
    partial_update=extend_schema(exclude=True),
    destroy=extend_schema(exclude=True),
)
class UserViewSet(viewsets.ViewSet):
    """
    Authentication + Profile API for all users.
    Follows API standards used across the project (CompanyView, SubscriptionView, etc.)
    """

    # ----------------------------------------
    # Permissions
    # ----------------------------------------
    def get_permissions(self):
        open_actions = ["signup", "signin", "token_refresh", "token_verify"]
        if self.action in open_actions:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    # ============================================================
    # SIGNUP
    # ============================================================

    @extend_schema(
    tags=["User Authentication"],
    summary="Register a new user (auto-login)",
    description="Creates a new user and automatically returns JWT tokens so user can immediately continue setup.",
    request=SignUpSerializer,
    responses={200: OpenApiResponse(description="User created + JWT tokens")},
    )
    @action(detail=False, methods=["post"], url_path="signup")
    def signup(self, request):
        try:
            serializer = SignUpSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                user = serializer.save()

            # -------------------------------
            # AUTO-LOGIN: GENERATE TOKENS 🎉
            # -------------------------------
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # Update last login timestamp
            user.last_login_date = timezone.now()
            user.save(update_fields=["last_login_date"])

            return api_response(
                0,
                "success",
                {
                    "user": UserSerializer(user).data,
                    "access": access_token,
                    "refresh": refresh_token,
                    "access_expires_in": refresh.access_token.lifetime.total_seconds(),
                },
            )

        except ValidationError as e:
            return api_response(
                1, "failure", {},
                "VALIDATION_ERROR",
                str(e.detail)
            )

        except Exception as e:
            logger.exception("Signup failed")
            return api_response(
                1, "failure", {},
                "SIGNUP_ERROR",
                str(e)
            )


    # ============================================================
    # SIGNIN
    # ============================================================

    @extend_schema(
        tags=["User Authentication"],
        summary="Sign in",
        request=SignInSerializer,
        responses={200: OpenApiResponse(description="JWT tokens + user info")},
    )
    @action(detail=False, methods=["post"], url_path="signin")
    def signin(self, request):
        try:
            serializer = SignInSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            email = serializer.validated_data["email"].lower().strip()
            password = serializer.validated_data["password"]

            # Authenticate with Django's backend
            user = authenticate(request=request, email=email, password=password)

            if not user:
                return api_response(
                    1, "failure", {},
                    "INVALID_CREDENTIALS",
                    "Invalid email or password."
                )

            # Check if active
            if getattr(user, "status", "").lower() != "active":
                return api_response(
                    1, "failure", {},
                    "INACTIVE_ACCOUNT",
                    "Your account is inactive."
                )

            # Update last login timestamp
            user.last_login_date = timezone.now()
            user.save(update_fields=["last_login_date"])

            # Create JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            return api_response(
                0, "success",
                {
                    "userId": str(user.userId),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                    "status": user.status,
                    "access": access_token,
                    "refresh": refresh_token,
                    "access_expires_in": refresh.access_token.lifetime.total_seconds()
                }
            )

        except Exception as e:
            logger.exception("Signin failed")
            return api_response(1, "failure", {}, "SIGNIN_ERROR", str(e))

    # ============================================================
    # SIGNOUT
    # ============================================================

    @extend_schema(
        tags=["User Authentication"],
        summary="Sign out user",
        request=SignOutSerializer,
    )
    @action(detail=False, methods=["post"], url_path="signout")
    def signout(self, request):
        try:
            serializer = SignOutSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user = request.user
            if not user or not user.is_authenticated:
                return api_response(1, "failure", {}, "UNAUTHORIZED", "User not authenticated.")

            provided_email = serializer.validated_data["email"]
            if user.email.lower() != provided_email.lower():
                return api_response(
                    1, "failure", {},
                    "EMAIL_MISMATCH",
                    "Provided email does not match authenticated user."
                )

            refresh_token = serializer.validated_data.get("refresh_token")

            # Blacklist refresh token if exists
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except Exception:
                    pass

            # Update last_updated_date
            user.last_updated_date = timezone.now()
            user.save(update_fields=["last_updated_date"])

            return api_response(0, "success", {"message": "Signed out successfully."})

        except Exception as e:
            logger.exception("Signout failed")
            return api_response(1, "failure", {}, "SIGNOUT_ERROR", str(e))

    # ============================================================
    # TOKEN REFRESH
    # ============================================================

    @extend_schema(
        tags=["Tokens"],
        summary="Refresh JWT token",
    )
    @action(detail=False, methods=["post"], url_path="token/refresh")
    def token_refresh(self, request):
        try:
            old_token = request.data.get("refresh")
            if not old_token:
                return api_response(1, "failure", {}, "MISSING_TOKEN", "Refresh token required.")

            try:
                old = RefreshToken(old_token)
            except TokenError:
                return api_response(1, "failure", {}, "INVALID_TOKEN", "Invalid refresh token.")

            user_id = old.get("user_id")
            if not user_id:
                return api_response(1, "failure", {}, "INVALID_TOKEN", "No user_id in token.")

            # Blacklist old
            try:
                old.blacklist()
            except Exception:
                pass

            user = User.objects.filter(userId=user_id).first()
            if not user:
                return api_response(1, "failure", {}, "USER_NOT_FOUND", "Token's user not found.")

            new_refresh = RefreshToken.for_user(user)

            return api_response(
                0, "success",
                {"access": str(new_refresh.access_token), "refresh": str(new_refresh)}
            )

        except Exception as e:
            logger.exception("Refresh failed")
            return api_response(1, "failure", {}, "TOKEN_REFRESH_ERROR", str(e))

    # ============================================================
    # VERIFY TOKEN
    # ============================================================

    @extend_schema(
        tags=["Tokens"],
        summary="Verify JWT token",
    )
    @action(detail=False, methods=["post"], url_path="token/verify")
    def token_verify(self, request):
        try:
            token_str = request.data.get("token")
            if not token_str:
                return api_response(1, "failure", {}, "MISSING_TOKEN", "Token required.")

            try:
                RefreshToken(token_str)
                return api_response(0, "success", {"valid": True})
            except Exception:
                return api_response(1, "failure", {}, "INVALID_TOKEN", "Token invalid or expired.")

        except Exception as e:
            logger.exception("Token verify failed")
            return api_response(1, "failure", {}, "TOKEN_VERIFY_ERROR", str(e))

    # ============================================================
    # PROFILE
    # ============================================================

    @extend_schema(
        tags=["User Profile"],
        summary="Get current user profile",
    )
    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return api_response(1, "failure", {}, "UNAUTHORIZED", "Not authenticated.")
        return api_response(0, "success", UserSerializer(user).data)

    # ============================================================
    # CHANGE PASSWORD
    # ============================================================

    @extend_schema(
        tags=["User Profile"],
        summary="Change password",
    )
    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request):
        try:
            user = request.user
            old_password = request.data.get("old_password")
            new_password = request.data.get("new_password")

            if not old_password or not new_password:
                return api_response(1, "failure", {}, "INVALID_INPUT", "Both passwords required.")

            if not check_password(old_password, user.password):
                return api_response(1, "failure", {}, "INVALID_OLD_PASSWORD", "Incorrect old password.")

            user.password = make_password(new_password)
            user.last_updated_date = timezone.now()
            user.save(update_fields=["password", "last_updated_date"])

            return api_response(0, "success", {"message": "Password updated."})

        except Exception as e:
            logger.exception("Password change failed")
            return api_response(1, "failure", {}, "CHANGE_PASSWORD_ERROR", str(e))

    # ============================================================
    # UPDATE PROFILE DETAILS
    # ============================================================

    @extend_schema(
        tags=["User Profile"],
        summary="Update user profile",
    )
    @action(detail=False, methods=["post"], url_path="update-details")
    def update_details(self, request):
        try:
            user = request.user
            allowed = [
                "first_name",
                "last_name",
                "phone",
                "profile_picture_url",
                "language_preference",
                "time_zone",
                "settings",
            ]

            updates = {k: v for k, v in request.data.items() if k in allowed}

            if not updates:
                return api_response(1, "failure", {}, "NO_FIELDS", "No valid fields provided.")

            for field, value in updates.items():
                setattr(user, field, value)

            user.last_updated_date = timezone.now()
            user.save(update_fields=list(updates.keys()) + ["last_updated_date"])

            return api_response(0, "success", {
                "message": "User details updated.",
                "user": UserSerializer(user).data
            })

        except Exception as e:
            logger.exception("Update profile failed")
            return api_response(1, "failure", {}, "UPDATE_DETAILS_ERROR", str(e))
