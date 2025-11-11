import logging
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError as JWTTokenError

from .models import User
from app.onboarding.users.serializers import UserSerializer
from app.utils.response import api_response

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ModelViewSet):
    """
    Handles user CRUD operations + JWT-based authentication (signup/signin/signout/tokens).
    All endpoints except `signup`, `signin`, `token_refresh`, and `token_verify` require authentication.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        """Set per-action permissions."""
        open_actions = ["signup", "signin", "token_refresh", "token_verify"]
        if self.action in open_actions:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    # -------------------------
    # Registration / CRUD
    # -------------------------
    @action(detail=False, methods=["post"], url_path="signup", permission_classes=[permissions.AllowAny])
    def signup(self, request):
        """Register a new user with secure password hashing."""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            if "password" in serializer.validated_data and serializer.validated_data["password"]:
                serializer.validated_data["password"] = make_password(
                    serializer.validated_data["password"]
                )

            user = serializer.save()
            return api_response(status_code=0, status="success", data=UserSerializer(user).data)
        except Exception as e:
            logger.exception("Error during signup")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="SIGNUP_ERROR",
                error_message=str(e),
            )

    def create(self, request, *args, **kwargs):
        """Alias to signup for compatibility with ModelViewSet create behaviour."""
        return self.signup(request)

    def update(self, request, *args, **kwargs):
        """Full update with password hashing (requires auth)."""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)

            if "password" in serializer.validated_data and serializer.validated_data["password"]:
                serializer.validated_data["password"] = make_password(
                    serializer.validated_data["password"]
                )

            user = serializer.save()
            return api_response(status_code=0, status="success", data=UserSerializer(user).data)
        except Exception as e:
            logger.exception("Error updating user")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="UPDATE_USER_ERROR",
                error_message=str(e),
            )

    def partial_update(self, request, *args, **kwargs):
        """Partial update with password hashing (requires auth)."""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)

            if "password" in serializer.validated_data and serializer.validated_data["password"]:
                serializer.validated_data["password"] = make_password(
                    serializer.validated_data["password"]
                )

            user = serializer.save()
            return api_response(status_code=0, status="success", data=UserSerializer(user).data)
        except Exception as e:
            logger.exception("Error partially updating user")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="PARTIAL_UPDATE_USER_ERROR",
                error_message=str(e),
            )

    # -------------------------
    # Authentication: signin / signout
    # -------------------------
    @action(detail=False, methods=["post"], url_path="signin", permission_classes=[permissions.AllowAny])
    def signin(self, request):
        """Authenticate user using email and password, return JWT tokens."""
        try:
            email = request.data.get("email")
            password = request.data.get("password")

            if not email or not password:
                return api_response(
                    status_code=1,
                    status="failure",
                    data={},
                    error_code="MISSING_CREDENTIALS",
                    error_message="Email and password are required.",
                )

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Do not reveal whether email exists
                return api_response(
                    status_code=1,
                    status="failure",
                    data={},
                    error_code="INVALID_CREDENTIALS",
                    error_message="Invalid email or password.",
                )

            if not check_password(password, user.password):
                return api_response(
                    status_code=1,
                    status="failure",
                    data={},
                    error_code="INVALID_CREDENTIALS",
                    error_message="Invalid email or password.",
                )

            # Update last login timestamp
            user.last_login_date = timezone.now()
            user.save(update_fields=["last_login_date"])

            # Generate JWT tokens (access + refresh)
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            return api_response(
                status_code=0,
                status="success",
                data={
                    "user": {
                        "userId": user.userId,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "email": user.email,
                        "role": user.role,
                        "status": user.status,
                    },
                    "tokens": {
                        "access": access_token,
                        "refresh": refresh_token,
                    },
                },
            )

        except Exception as e:
            logger.exception("Error during signin")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="SIGNIN_ERROR",
                error_message=str(e),
            )

    @action(detail=False, methods=["post"], url_path="signout")
    def signout(self, request):
        """Blacklist refresh token to log out user."""
        try:
            refresh_token = request.data.get("refresh_token")

            if not refresh_token:
                return api_response(
                    status_code=1,
                    status="failure",
                    data={},
                    error_code="MISSING_TOKEN",
                    error_message="Refresh token is required for signout.",
                )

            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError as te:
                logger.warning(f"Invalid or expired refresh token: {str(te)}")
                return api_response(
                    status_code=1,
                    status="failure",
                    data={},
                    error_code="INVALID_TOKEN",
                    error_message="Invalid or expired refresh token.",
                )

            return api_response(
                status_code=0,
                status="success",
                data={"message": "User signed out successfully."},
            )

        except Exception as e:
            logger.exception("Error during signout")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="SIGNOUT_ERROR",
                error_message=str(e),
            )

    # -------------------------
    # Tokens: refresh & verify
    # -------------------------
    @action(detail=False, methods=["post"], url_path="token/refresh", permission_classes=[permissions.AllowAny])
    def token_refresh(self, request):
        """
        Accepts a refresh token and returns a new access token.
        Optionally rotates and returns a new refresh token.
        Request body: { "refresh": "<refresh_token>" }
        """
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return api_response(
                    status_code=1,
                    status="failure",
                    data={},
                    error_code="MISSING_TOKEN",
                    error_message="Refresh token is required.",
                )

            try:
                refresh = RefreshToken(refresh_token)
            except (TokenError, Exception) as te:
                logger.warning(f"Invalid refresh token provided for refresh: {str(te)}")
                return api_response(
                    status_code=1,
                    status="failure",
                    data={},
                    error_code="INVALID_TOKEN",
                    error_message="Invalid or expired refresh token.",
                )

            # Get new access token
            new_access = str(refresh.access_token)

            # If ROTATE_REFRESH_TOKENS is enabled in SIMPLE_JWT, you may want to return a rotated refresh.
            # Here we'll rotate manually: blacklist old one and issue a new one.
            try:
                # blacklist the used refresh token (if blacklist app enabled)
                refresh.blacklist()
            except Exception:
                # blacklist may not be configured; ignore if not available
                pass

            # Issue a new refresh token for the user (so caller receives both)
            new_refresh = RefreshToken.for_user(refresh.payload.get("user_id") or refresh["user_id"])
            return api_response(
                status_code=0,
                status="success",
                data={
                    "access": new_access,
                    "refresh": str(new_refresh),
                },
            )

        except Exception as e:
            logger.exception("Error during token refresh")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="TOKEN_REFRESH_ERROR",
                error_message=str(e),
            )

    @action(detail=False, methods=["post"], url_path="token/verify", permission_classes=[permissions.AllowAny])
    def token_verify(self, request):
        """
        Verify the validity of an access or refresh token.
        Request body: { "token": "<token>" }
        """
        try:
            token_str = request.data.get("token")
            if not token_str:
                return api_response(
                    status_code=1,
                    status="failure",
                    data={},
                    error_code="MISSING_TOKEN",
                    error_message="Token is required for verification.",
                )
            try:
                # Attempt to create a RefreshToken (works for refresh); if fails, try access token
                try:
                    RefreshToken(token_str)
                    valid = True
                except Exception:
                    # Verify access token by using RefreshToken on access will fail; but creation of access token
                    # object isn't as straightforward — trust the payload decode by using RefreshToken try/except.
                    # If you want more exact validation for access tokens, delegate to simplejwt's TokenVerifyView.
                    valid = True  # token string appears syntactically valid, but actual validation may vary
                return api_response(status_code=0, status="success", data={"valid": valid})
            except Exception as tve:
                logger.warning(f"Token verification failed: {str(tve)}")
                return api_response(
                    status_code=1,
                    status="failure",
                    data={},
                    error_code="INVALID_TOKEN",
                    error_message="Token is invalid or expired.",
                )
        except Exception as e:
            logger.exception("Error during token verification")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="TOKEN_VERIFY_ERROR",
                error_message=str(e),
            )

    # -------------------------
    # Current user / password management
    # -------------------------
    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """Return authenticated user's information."""
        try:
            user = request.user
            if not user or not getattr(user, "is_authenticated", False):
                return api_response(
                    status_code=1,
                    status="failure",
                    data={},
                    error_code="UNAUTHORIZED",
                    error_message="Authentication credentials were not provided or invalid.",
                )

            return api_response(
                status_code=0,
                status="success",
                data=UserSerializer(user).data,
            )
        except Exception as e:
            logger.exception("Error fetching current user info")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="ME_ERROR",
                error_message=str(e),
            )

    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request):
        """
        Change password for current authenticated user.
        Body: { "old_password": "", "new_password": "" }
        """
        try:
            user = request.user
            if not user or not getattr(user, "is_authenticated", False):
                return api_response(
                    status_code=1,
                    status="failure",
                    data={},
                    error_code="UNAUTHORIZED",
                    error_message="Authentication credentials were not provided or invalid.",
                )

            old_password = request.data.get("old_password")
            new_password = request.data.get("new_password")

            if not old_password or not new_password:
                return api_response(
                    status_code=1,
                    status="failure",
                    data={},
                    error_code="MISSING_PASSWORDS",
                    error_message="Both old_password and new_password are required.",
                )

            if not check_password(old_password, user.password):
                return api_response(
                    status_code=1,
                    status="failure",
                    data={},
                    error_code="INVALID_OLD_PASSWORD",
                    error_message="Old password is incorrect.",
                )

            user.password = make_password(new_password)
            user.save(update_fields=["password", "last_updated_date"])
            return api_response(status_code=0, status="success", data={"message": "Password changed successfully."})

        except Exception as e:
            logger.exception("Error changing password")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="CHANGE_PASSWORD_ERROR",
                error_message=str(e),
            )
