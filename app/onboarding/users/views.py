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
from django.conf import settings

from .models import User
from .serializers import (
    SignInSerializer,
    SignUpSerializer,
    SignOutSerializer,
    UserPublicSerializer,
    UserProfileUpdateSerializer,
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

    # ----------------------------------------
    # Permissions
    # ----------------------------------------
    def get_permissions(self):
        open_actions = ["signup", "signin", "token_refresh", "token_verify"]
        if self.action in open_actions:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    # ============================================================
    # SIGNUP — RETURNS USER + ACCESS TOKEN + SETS REFRESH COOKIE
    # ============================================================
    @extend_schema(
        tags=["User Authentication"],
        summary="Register new user (auto-login)",
        request=SignUpSerializer,
        responses={200: OpenApiResponse(description="User created + tokens")},
    )
    @action(detail=False, methods=["post"], url_path="signup")
    def signup(self, request):
        try:
            serializer = SignUpSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                user = serializer.save()

            # Create tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # Update last login
            user.last_login_date = timezone.now()
            user.save(update_fields=["last_login_date"])

            response_payload = {
                "user": UserPublicSerializer(user).data,
                "access": access_token,
            }

            res = api_response(
                status_code=status.HTTP_200_OK,
                status="success",
                data=response_payload
            )

            # Apply cookie settings
            cookie_name = settings.SIMPLE_JWT.get("AUTH_COOKIE", "oi_refresh_token")
            res.set_cookie(
                key=cookie_name,
                value=refresh_token,
                httponly=settings.SIMPLE_JWT.get("AUTH_COOKIE_HTTP_ONLY", True),
                secure=settings.SIMPLE_JWT.get("AUTH_COOKIE_SECURE", False),
                samesite=settings.SIMPLE_JWT.get("AUTH_COOKIE_SAMESITE", "Lax"),
                path=settings.SIMPLE_JWT.get("AUTH_COOKIE_PATH", "/"),
            )

            return res

        except ValidationError as e:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="failure",
                data={},
                error_code="VALIDATION_ERROR",
                error_message=str(e.detail)
            )
        except Exception as e:
            logger.exception("Signup failed")
            return api_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="failure",
                data={},
                error_code="SIGNUP_ERROR",
                error_message=str(e)
            )

    # ============================================================
    # SIGNIN — RETURNS USER + ACCESS TOKEN + SETS REFRESH COOKIE
    # ============================================================
    @extend_schema(
        tags=["User Authentication"],
        summary="Sign in",
        request=SignInSerializer,
        responses={200: OpenApiResponse(description="Sign in successful")},
    )
    @action(detail=False, methods=["post"], url_path="signin")
    def signin(self, request):
        try:
            serializer = SignInSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            email = serializer.validated_data["email"].lower().strip()
            password = serializer.validated_data["password"]

            user = authenticate(request=request, email=email, password=password)

            if not user:
                return api_response(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    status="failure",
                    data={},
                    error_code="INVALID_CREDENTIALS",
                    error_message="Invalid email or password."
                )

            if getattr(user, "status", "").lower() != "active":
                return api_response(
                    status_code=status.HTTP_403_FORBIDDEN,
                    status="failure",
                    data={},
                    error_code="INACTIVE_ACCOUNT",
                    error_message="Your account is inactive."
                )

            user.last_login_date = timezone.now()
            user.save(update_fields=["last_login_date"])

            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            response_payload = {
                "user": UserPublicSerializer(user).data,
                "access": access_token,
            }

            res = api_response(
                status_code=status.HTTP_200_OK,
                status="success",
                data=response_payload
            )

            res.set_cookie(
                key=settings.SIMPLE_JWT.get("AUTH_COOKIE", "oi_refresh_token"),
                value=refresh_token,
                httponly=settings.SIMPLE_JWT.get("AUTH_COOKIE_HTTP_ONLY", True),
                secure=settings.SIMPLE_JWT.get("AUTH_COOKIE_SECURE", False),
                samesite=settings.SIMPLE_JWT.get("AUTH_COOKIE_SAMESITE", "Lax"),
                path=settings.SIMPLE_JWT.get("AUTH_COOKIE_PATH", "/"),
            )

            return res

        except Exception as e:
            logger.exception("Signin failed")
            return api_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="failure",
                data={},
                error_code="SIGNIN_ERROR",
                error_message=str(e)
            )

    # ============================================================
    # SIGNOUT — DELETE REFRESH COOKIE
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

            response = api_response(
                status_code=status.HTTP_200_OK,
                status="success",
                data={"message": "Signed out successfully."}
            )

            response.delete_cookie(
                key=settings.SIMPLE_JWT["AUTH_COOKIE"],
                path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
            )
            return response

        except Exception as e:
            logger.exception("Signout failed")
            return api_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="failure",
                data={},
                error_code="SIGNOUT_ERROR",
                error_message=str(e)
            )

    # ============================================================
    # TOKEN REFRESH — ROTATE COOKIE + RETURN ACCESS TOKEN
    # ============================================================
    @extend_schema(
        tags=["Tokens"],
        summary="Refresh access token (HttpOnly cookie)",
        responses={200: OpenApiResponse(description="New access token")},
    )
    @action(detail=False, methods=["post"], url_path="token/refresh")
    def token_refresh(self, request):
        try:
            cookie_name = settings.SIMPLE_JWT.get("AUTH_COOKIE", "oi_refresh_token")
            refresh_token = request.COOKIES.get(cookie_name)

            if not refresh_token:
                return api_response(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status="failure",
                    data={},
                    error_code="MISSING_REFRESH_TOKEN",
                    error_message="Refresh cookie missing."
                )

            try:
                old_refresh = RefreshToken(refresh_token)
            except TokenError:
                return api_response(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    status="failure",
                    data={},
                    error_code="INVALID_REFRESH",
                    error_message="Invalid refresh token."
                )

            # Extract user_id from token
            user_id_claim = settings.SIMPLE_JWT.get("USER_ID_CLAIM", "user_id")
            user_id = old_refresh.payload.get(user_id_claim)

            if not user_id:
                return api_response(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    status="failure",
                    data={},
                    error_code="INVALID_TOKEN",
                    error_message="Could not extract user_id."
                )

            # Rotate refresh
            user = User.objects.filter(userId=user_id).first()
            if not user:
                return api_response(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="failure",
                    data={},
                    error_code="USER_NOT_FOUND",
                    error_message="Token user does not exist."
                )

            new_refresh = RefreshToken.for_user(user)
            new_access = str(new_refresh.access_token)

            res = api_response(
                status_code=status.HTTP_200_OK,
                status="success",
                data={"access": new_access}
            )

            res.set_cookie(
                key=cookie_name,
                value=str(new_refresh),
                httponly=settings.SIMPLE_JWT.get("AUTH_COOKIE_HTTP_ONLY", True),
                secure=settings.SIMPLE_JWT.get("AUTH_COOKIE_SECURE", False),
                samesite=settings.SIMPLE_JWT.get("AUTH_COOKIE_SAMESITE", "Lax"),
                path=settings.SIMPLE_JWT.get("AUTH_COOKIE_PATH", "/"),
            )

            return res

        except Exception as e:
            logger.exception("Refresh failed")
            return api_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="failure",
                data={},
                error_code="REFRESH_ERROR",
                error_message=str(e)
            )

    # ============================================================
    # UPDATE AUTHENTICATED USER PROFILE
    # ============================================================
    @extend_schema(
        tags=["User Profile"],
        summary="Update your own profile",
        request=UserProfileUpdateSerializer,
        responses={200: OpenApiResponse(description="Profile updated")},
    )
    @action(detail=False, methods=["put"], url_path="me/update")
    def update_me(self, request):
        try:
            serializer = UserProfileUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            updates = serializer.validated_data

            user = request.user

            allowed = [
                "first_name",
                "last_name",
                "email",
                "phone",
                "profile_picture_url",
                "language_preference",
                "time_zone",
                "settings",
            ]

            changed = False
            for f in allowed:
                if f in updates:
                    setattr(user, f, updates[f])
                    changed = True

            if changed:
                user.last_updated_date = timezone.now()
                user.save()

            return api_response(
                0,
                "success",
                {
                    "message": "Profile updated successfully",
                    "user": UserPublicSerializer(user).data,
                }
            )

        except Exception as e:
            logger.exception("Profile update failed")
            return api_response(
                1,
                "failure",
                {},
                "PROFILE_UPDATE_ERROR",
                str(e)
            )
