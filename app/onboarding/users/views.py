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

    # ----------------------------------------
    # Permissions
    # ----------------------------------------
    def get_permissions(self):
        open_actions = ["signup", "signin", "token_refresh", "token_verify"]
        if self.action in open_actions:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    # ============================================================
    # SIGNUP — SETS REFRESH HTTPONLY COOKIE
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

            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            user.last_login_date = timezone.now()
            user.save(update_fields=["last_login_date"])

            response_data = {
                "user": UserSerializer(user).data,
                "access": access_token,
                "access_expires_in": refresh.access_token.lifetime.total_seconds(),
            }

            res = api_response(0, "success", response_data)

            # Set HttpOnly refresh cookie
            res.set_cookie(
                key=settings.SIMPLE_JWT["AUTH_COOKIE"],
                value=str(refresh),
                httponly=True,
                secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
                samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
                path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
            )

            return res

        except ValidationError as e:
            return api_response(1, "failure", {}, "VALIDATION_ERROR", str(e.detail))

        except Exception as e:
            logger.exception("Signup failed")
            return api_response(1, "failure", {}, "SIGNUP_ERROR", str(e))


    # ============================================================
    # SIGNIN — SETS REFRESH HTTPONLY COOKIE
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
                return api_response(1, "failure", {}, "INVALID_CREDENTIALS", "Invalid email or password.")

            if user.status.lower() != "active":
                return api_response(1, "failure", {}, "INACTIVE_ACCOUNT", "Your account is inactive.")

            user.last_login_date = timezone.now()
            user.save(update_fields=["last_login_date"])

            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            response_data = {
                "userId": str(user.userId),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "status": user.status,
                "access": access_token,
                "access_expires_in": refresh.access_token.lifetime.total_seconds(),
            }

            res = api_response(0, "success", response_data)

            # Set HttpOnly refresh cookie
            res.set_cookie(
                key=settings.SIMPLE_JWT["AUTH_COOKIE"],
                value=str(refresh),
                httponly=True,
                secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
                samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
                path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
            )

            return res

        except Exception as e:
            logger.exception("Signin failed")
            return api_response(1, "failure", {}, "SIGNIN_ERROR", str(e))


    # ============================================================
    # SIGNOUT — DELETE COOKIE
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

            response = api_response(0, "success", {"message": "Signed out successfully."})

            # Delete refresh cookie
            response.delete_cookie(
                key=settings.SIMPLE_JWT["AUTH_COOKIE"],
                path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
            )

            return response

        except Exception as e:
            logger.exception("Signout failed")
            return api_response(1, "failure", {}, "SIGNOUT_ERROR", str(e))


    # ============================================================
    # TOKEN REFRESH — READ FROM COOKIE, ROTATE COOKIE
    # ============================================================

    @extend_schema(
        tags=["Tokens"],
        summary="Refresh access token (HttpOnly cookie)",
    )
    @action(detail=False, methods=["post"], url_path="token/refresh")
    def token_refresh(self, request):
        try:
            cookie_name = settings.SIMPLE_JWT["AUTH_COOKIE"]
            refresh_token = request.COOKIES.get(cookie_name)

            if not refresh_token:
                return api_response(1, "failure", {}, "MISSING_REFRESH_TOKEN", "Refresh cookie missing.")

            try:
                refresh = RefreshToken(refresh_token)
            except TokenError:
                return api_response(1, "failure", {}, "INVALID_REFRESH", "Invalid refresh token.")

            # Create access token
            access = str(refresh.access_token)

            # Rotate refresh
            new_refresh = RefreshToken.for_user(refresh.access_token.payload["user_id"])

            res = api_response(0, "success", {"access": access})

            # Store new refresh cookie
            res.set_cookie(
                key=cookie_name,
                value=str(new_refresh),
                httponly=True,
                secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
                samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
                path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
            )

            return res

        except Exception as e:
            logger.exception("Refresh failed")
            return api_response(1, "failure", {}, "REFRESH_ERROR", str(e))


    # ============================================================
    # token_verify — unchanged
    # profile — unchanged
    # change_password — unchanged
    # update_details — unchanged
    # ============================================================
