import logging
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from rest_framework import viewsets, status, permissions, serializers
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import User
from app.onboarding.users.serializers import UserSerializer, SignInSerializer, SignUpSerializer, SignOutSerializer
from app.utils.response import api_response
from rest_framework.exceptions import ValidationError



logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(exclude=True),
    retrieve=extend_schema(exclude=True),
    update=extend_schema(exclude=True),
    partial_update=extend_schema(exclude=True),
    destroy=extend_schema(exclude=True),
)
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

    # ----------------------------------------------------------------------
    # AUTHENTICATION ENDPOINTS
    # ----------------------------------------------------------------------

    @extend_schema(
        tags=["User Authentication"],
        summary="Register a new user",
        description="Creates a new user account with normalized lowercase email and securely hashed password.",
        request=SignUpSerializer,  # ✅ Show only email, password, name, phone
        responses={200: UserSerializer},
    )
    @action(detail=False, methods=["post"], url_path="signup", permission_classes=[permissions.AllowAny])
    def signup(self, request):
        """Register a new user."""
        try:
            serializer = SignUpSerializer(data=request.data)  # ✅ Use dedicated serializer
            serializer.is_valid(raise_exception=True)

            user = serializer.save()

            return api_response(
                status_code=0,
                status="success",
                data=UserSerializer(user).data
            )

        except ValidationError as e:
            error_message = (
                e.detail if isinstance(e.detail, str)
                else " ".join([f"{key}: {', '.join(val)}" for key, val in e.detail.items()])
            )
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="VALIDATION_ERROR",
                error_message=error_message,
            )

        except Exception as e:
            logger.exception("Error during signup")
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="SIGNUP_ERROR",
                error_message=str(e),
            )


    @extend_schema(
        tags=["User Authentication"],
        summary="Sign in user",
        description="Authenticate using email and password (case-insensitive) to receive access and refresh JWT tokens.",
        request=SignInSerializer,
        responses={200: UserSerializer},
    )
    @action(detail=False, methods=["post"], url_path="signin", permission_classes=[permissions.AllowAny])
    def signin(self, request):
        """Authenticate user using email and password, return JWT tokens."""
        try:
            serializer = SignInSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            email = serializer.validated_data["email"].strip().lower()
            password = serializer.validated_data["password"]

            # 🔍 Fetch user by normalized email
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                return api_response(
                    status_code=1,
                    status="failure",
                    data={},
                    error_code="INVALID_CREDENTIALS",
                    error_message="Invalid email or password.",
                )

            # 🔐 Validate password
            if not check_password(password, user.password):
                return api_response(
                    status_code=1,
                    status="failure",
                    data={},
                    error_code="INVALID_CREDENTIALS",
                    error_message="Invalid email or password.",
                )

            # 🕒 Update last login time
            user.last_login_date = timezone.now()
            user.save(update_fields=["last_login_date"])

            # 🪪 Generate JWT tokens manually (compatible with UUID)
            refresh = RefreshToken()
            refresh["user_id"] = str(user.userId)
            refresh["email"] = user.email

            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # ✅ Successful response
            return api_response(
                status_code=0,
                status="success",
                data={
                    "userId": str(user.userId),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                    "status": user.status,
                    "access": access_token,
                    "refresh": refresh_token,
                },
            )

        except ValidationError as e:
            error_message = (
                e.detail if isinstance(e.detail, str)
                else " ".join([f"{key}: {', '.join(val)}" for key, val in e.detail.items()])
            )
            return api_response(
                status_code=1,
                status="failure",
                data={},
                error_code="VALIDATION_ERROR",
                error_message=error_message,
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

    
    @extend_schema(
        tags=["User Authentication"],
        summary="Sign out user",
        description=(
            "Signs out the authenticated user. "
            "Validates email and optionally blacklists the provided refresh token."
        ),
        request=SignOutSerializer,
    )
    @action(detail=False, methods=["post"], url_path="signout")
    def signout(self, request):
        """Logout authenticated user — validates email and optionally blacklists refresh token."""
        try:
            serializer = SignOutSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            email = serializer.validated_data["email"]
            refresh_token = serializer.validated_data.get("refresh_token", "")

            # ✅ Ensure the access token belongs to the same user
            user = request.user
            if not user or not user.is_authenticated:
                return api_response(1, "failure", {}, "UNAUTHORIZED", "Authentication required.")

            if user.email.lower() != email.lower():
                return api_response(
                    1,
                    "failure",
                    {},
                    "EMAIL_MISMATCH",
                    "Email does not match the authenticated user.",
                )

            # ✅ Optional: blacklist refresh token if provided
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except TokenError:
                    return api_response(
                        1, "failure", {}, "INVALID_TOKEN", "Invalid or expired refresh token."
                    )

            # ✅ Update last activity
            user.last_updated_date = timezone.now()
            user.save(update_fields=["last_updated_date"])

            return api_response(
                0,
                "success",
                {"message": "User signed out successfully."},
            )

        except ValidationError as e:
            error_message = (
                e.detail if isinstance(e.detail, str)
                else " ".join([f"{key}: {', '.join(val)}" for key, val in e.detail.items()])
            )
            return api_response(
                1, "failure", {}, "VALIDATION_ERROR", error_message
            )

        except Exception as e:
            logger.exception("Error during signout")
            return api_response(
                1, "failure", {}, "SIGNOUT_ERROR", str(e)
            )

        

    # ----------------------------------------------------------------------
    # TOKEN ENDPOINTS
    # ----------------------------------------------------------------------

    @extend_schema(
        tags=["Tokens"],
        summary="Refresh JWT token",
        description="Accepts a refresh token and returns a new access token. Optionally rotates refresh token."
    )
    @action(detail=False, methods=["post"], url_path="token/refresh", permission_classes=[permissions.AllowAny])
    def token_refresh(self, request):
        """Refresh JWT token."""
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return api_response(1, "failure", {}, "MISSING_TOKEN", "Refresh token is required.")

            refresh = RefreshToken(refresh_token)
            new_access = str(refresh.access_token)

            try:
                refresh.blacklist()
            except Exception:
                pass

            new_refresh = RefreshToken.for_user(refresh.payload.get("user_id") or refresh["user_id"])
            return api_response(0, "success", {"access": new_access, "refresh": str(new_refresh)})
        except Exception as e:
            logger.exception("Error during token refresh")
            return api_response(1, "failure", {}, "TOKEN_REFRESH_ERROR", str(e))

    @extend_schema(
        tags=["Tokens"],
        summary="Verify JWT token",
        description="Verifies the validity of a given JWT token (access or refresh)."
    )
    @action(detail=False, methods=["post"], url_path="token/verify", permission_classes=[permissions.AllowAny])
    def token_verify(self, request):
        """Verify token validity."""
        try:
            token_str = request.data.get("token")
            if not token_str:
                return api_response(1, "failure", {}, "MISSING_TOKEN", "Token is required for verification.")
            try:
                RefreshToken(token_str)
                return api_response(0, "success", {"valid": True})
            except Exception:
                return api_response(1, "failure", {}, "INVALID_TOKEN", "Token is invalid or expired.")
        except Exception as e:
            logger.exception("Error verifying token")
            return api_response(1, "failure", {}, "TOKEN_VERIFY_ERROR", str(e))

    # ----------------------------------------------------------------------
    # PROFILE / ACCOUNT MANAGEMENT
    # ----------------------------------------------------------------------

    @extend_schema(
        tags=["User Profile"],
        summary="Get current user profile",
        description="Returns the profile of the currently authenticated user."
    )
    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """Return current user info."""
        try:
            user = request.user
            if not user or not getattr(user, "is_authenticated", False):
                return api_response(1, "failure", {}, "UNAUTHORIZED", "User not authenticated.")
            return api_response(0, "success", UserSerializer(user).data)
        except Exception as e:
            logger.exception("Error fetching user info")
            return api_response(1, "failure", {}, "ME_ERROR", str(e))

    @extend_schema(
        tags=["User Profile"],
        summary="Change password",
        description="Change the password for the authenticated user."
    )
    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request):
        """Change password."""
        try:
            user = request.user
            old_password = request.data.get("old_password")
            new_password = request.data.get("new_password")
            if not old_password or not new_password:
                return api_response(1, "failure", {}, "MISSING_PASSWORDS", "Both old and new passwords are required.")
            if not check_password(old_password, user.password):
                return api_response(1, "failure", {}, "INVALID_OLD_PASSWORD", "Old password is incorrect.")

            user.password = make_password(new_password)
            user.save(update_fields=["password", "last_updated_date"])
            return api_response(0, "success", {"message": "Password changed successfully."})
        except Exception as e:
            logger.exception("Error changing password")
            return api_response(1, "failure", {}, "CHANGE_PASSWORD_ERROR", str(e))

    @extend_schema(
        tags=["User Profile"],
        summary="Update user details",
        description="Updates personal details (first name, last name, phone, language, timezone, etc.) for the authenticated user."
    )
    @action(detail=False, methods=["post"], url_path="update-details")
    def update_details(self, request):
        """Update user profile details."""
        try:
            user = request.user
            allowed_fields = [
                "first_name", "last_name", "phone", "profile_picture_url",
                "language_preference", "time_zone", "settings"
            ]
            updates = {k: v for k, v in request.data.items() if k in allowed_fields}
            if not updates:
                return api_response(1, "failure", {}, "NO_FIELDS_PROVIDED", "No valid fields provided for update.")

            for field, value in updates.items():
                setattr(user, field, value)
            user.save(update_fields=list(updates.keys()) + ["last_updated_date"])

            return api_response(0, "success", {"message": "User details updated successfully.", "user": UserSerializer(user).data})
        except Exception as e:
            logger.exception("Error updating user details")
            return api_response(1, "failure", {}, "UPDATE_DETAILS_ERROR", str(e))
