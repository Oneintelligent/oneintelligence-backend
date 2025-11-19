import logging
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import authenticate
from rest_framework import permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import ValidationError as SerializerValidationError
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse

from django.core.mail import send_mail

from app.platform.accounts.models import (
    User, InviteToken, EmailVerificationToken, PasswordResetToken
)
from app.platform.accounts.serializers import (
    SignUpSerializer,
    SignInSerializer,
    UserWithCompanySerializer,
    UserProfileUpdateSerializer,
    InviteUserSerializer,
    AcceptInviteSerializer,
    TeamMemberUpdateSerializer,
    MiniUserSerializer,
)

from app.utils.response import api_response
from app.utils.exception_handler import format_validation_error

logger = logging.getLogger(__name__)



@extend_schema_view(
    list=extend_schema(exclude=True),
    retrieve=extend_schema(exclude=True),
    update=extend_schema(exclude=True),
    partial_update=extend_schema(exclude=True),
    destroy=extend_schema(exclude=True),
)
class UserViewSet(viewsets.ViewSet):
    """
    Action-Oriented ViewSet for user auth and profile.
    """

    def get_permissions(self):
        open_actions = [
            "signup", "signin", "token_refresh", "accept_invite",
            "forgot_password", "reset_password", "verify_email", "resend_verification"
        ]
        if getattr(self, "action", None) in open_actions:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    # -------------------------------------------------------
    # Helpers
    # -------------------------------------------------------
    def _set_refresh_cookie(self, response, refresh_token: str):
        cookie_name = settings.SIMPLE_JWT.get("AUTH_COOKIE", "oi_refresh_token")
        cookie_path = settings.SIMPLE_JWT.get("AUTH_COOKIE_PATH", "/")

        response.set_cookie(
            key=cookie_name,
            value=refresh_token,
            httponly=True,
            secure=settings.SIMPLE_JWT.get("AUTH_COOKIE_SECURE", False),
            samesite=settings.SIMPLE_JWT.get("AUTH_COOKIE_SAMESITE", "Lax"),
            path=cookie_path,
        )

    def _handle_exception(self, exc: Exception, where: str = ""):
        logger.exception("%s: %s", where, str(exc))
        
        # Handle validation errors with readable messages
        if isinstance(exc, (ValidationError, SerializerValidationError)):
            error_message = format_validation_error(exc.detail)
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="failure",
                data={},
                error_code="VALIDATION_ERROR",
                error_message=error_message,
            )
        
        # Handle other exceptions
        # Try to extract a readable message
        error_message = str(exc)
        if hasattr(exc, 'detail'):
            error_message = format_validation_error(exc.detail) if isinstance(exc.detail, (dict, list)) else str(exc.detail)
        
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            status="failure",
            data={},
            error_code="SERVER_ERROR",
            error_message=error_message,
        )

    # -------------------------------------------------------
    # Sign Up
    # -------------------------------------------------------
    @extend_schema(tags=["Auth"], summary="Register new user", request=SignUpSerializer)
    @action(detail=False, methods=["post"], url_path="signup")
    def signup(self, request):
        try:
            serializer = SignUpSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                user = serializer.save()
                # Create email verification token
                EmailVerificationToken.objects.filter(user=user).delete()
                verification_token = EmailVerificationToken.create_for_user(user, hours_valid=24)
                
                # Send verification email
                try:
                    frontend_url = settings.FRONTEND_BASE
                    verify_link = f"{frontend_url}/auth/verify-email?token={verification_token.token}"
                    send_mail(
                        "Verify your email address",
                        f"Click to verify: {verify_link}",
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                    )
                except Exception:
                    logger.exception("Failed to send verification email")

            refresh = RefreshToken.for_user(user)
            access = str(refresh.access_token)

            # refresh last_login
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])

            # Refresh user from DB with company relationship to ensure latest data
            user = User.objects.select_related("company").get(userId=user.userId)

            payload = {
                "user": UserWithCompanySerializer(user).data,
                "access": access,
            }
            res = api_response(200, "success", payload)
            self._set_refresh_cookie(res, str(refresh))
            return res

        except Exception as exc:
            return self._handle_exception(exc, "signup")

    # -------------------------------------------------------
    # Sign In
    # -------------------------------------------------------
    @extend_schema(tags=["Auth"], summary="Sign in", request=SignInSerializer)
    @action(detail=False, methods=["post"], url_path="signin")
    def signin(self, request):
        try:
            serializer = SignInSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            email = serializer.validated_data["email"]
            password = serializer.validated_data["password"]

            # Check if account is locked
            try:
                user = User.objects.get(email__iexact=email)
                if user.is_account_locked():
                    return api_response(
                        423, "failure", {},
                        "ACCOUNT_LOCKED",
                        f"Account is locked until {user.account_locked_until}. Please try again later."
                    )
            except User.DoesNotExist:
                pass

            # username=<email>
            user = authenticate(request=request, username=email, password=password)

            if not user:
                # Record failed attempt if user exists
                try:
                    user_obj = User.objects.get(email__iexact=email)
                    user_obj.record_failed_login()
                except User.DoesNotExist:
                    pass
                return api_response(
                    401, "failure", {},
                    "INVALID_CREDENTIALS",
                    "Invalid email or password."
                )

            # Check account status
            if user.status != User.Status.ACTIVE:
                return api_response(
                    403, "failure", {},
                    "INACTIVE_ACCOUNT",
                    "This account is inactive."
                )

            # Record successful login and unlock if needed
            user.record_successful_login()

            refresh = RefreshToken.for_user(user)
            access = str(refresh.access_token)

            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])

            # Refresh user from DB with company relationship to ensure latest data
            user = User.objects.select_related("company").get(userId=user.userId)

            payload = {"user": UserWithCompanySerializer(user).data, "access": access}
            res = api_response(200, "success", payload)
            self._set_refresh_cookie(res, str(refresh))
            return res

        except Exception as exc:
            return self._handle_exception(exc, "signin")

    # -------------------------------------------------------
    # Sign Out
    # -------------------------------------------------------
    @extend_schema(tags=["Auth"], summary="Sign out")
    @action(detail=False, methods=["post"], url_path="signout")
    def signout(self, request):
        try:
            res = api_response(200, "success", {"message": "Signed out"})
            cookie_name = settings.SIMPLE_JWT.get("AUTH_COOKIE", "oi_refresh_token")
            cookie_path = settings.SIMPLE_JWT.get("AUTH_COOKIE_PATH", "/")
            res.delete_cookie(cookie_name, path=cookie_path)
            return res
        except Exception as exc:
            return self._handle_exception(exc, "signout")

    # -------------------------------------------------------
    # Refresh Token
    # -------------------------------------------------------
    @extend_schema(tags=["Auth"], summary="Refresh JWT access token")
    @action(detail=False, methods=["post"], url_path="token/refresh")
    def token_refresh(self, request):
        try:
            cookie_name = settings.SIMPLE_JWT.get("AUTH_COOKIE", "oi_refresh_token")
            refresh_token = request.COOKIES.get(cookie_name)

            if not refresh_token:
                return api_response(400, "failure", {}, "NO_REFRESH_TOKEN", "Refresh cookie missing")

            try:
                old = RefreshToken(refresh_token)
            except TokenError:
                return api_response(401, "failure", {}, "INVALID_REFRESH", "Invalid refresh token")

            # Get userId from token payload (matches SIMPLE_JWT USER_ID_CLAIM)
            user_id = old.payload.get("userId") or old.payload.get("user_id")
            if not user_id:
                return api_response(401, "failure", {}, "INVALID_TOKEN", "Token missing user identifier")
            
            user = User.objects.filter(userId=user_id).first()
            if not user:
                return api_response(404, "failure", {}, "USER_NOT_FOUND", "User not found")

            new_refresh = RefreshToken.for_user(user)
            access = str(new_refresh.access_token)

            res = api_response(200, "success", {"access": access})
            self._set_refresh_cookie(res, str(new_refresh))
            return res

        except Exception as exc:
            return self._handle_exception(exc, "token_refresh")

    # -------------------------------------------------------
    # Current User (me)
    # -------------------------------------------------------
    @extend_schema(tags=["Users"], summary="Get authenticated user")
    @action(detail=False, methods=["get"], url_path="me")
    def get_me(self, request):
        try:
            user = User.objects.select_related("company").get(userId=request.user.userId)
            return api_response(200, "success", UserWithCompanySerializer(user).data)
        except Exception as exc:
            return self._handle_exception(exc, "get_me")

    # -------------------------------------------------------
    # Update Me
    # -------------------------------------------------------
    @extend_schema(tags=["Users"], summary="Update current user profile")
    @action(detail=False, methods=["put"], url_path="me/update")
    def update_me(self, request):
        try:
            serializer = UserProfileUpdateSerializer(
                data=request.data,
                context={"request": request}
            )
            serializer.is_valid(raise_exception=True)

            user = request.user
            for key, value in serializer.validated_data.items():
                setattr(user, key, value)

            user.last_updated_date = timezone.now()
            user.save()

            # Refresh user from DB with company relationship to ensure latest data
            user = User.objects.select_related("company").get(userId=user.userId)

            return api_response(
                200, "success",
                {"message": "Profile updated", "user": UserWithCompanySerializer(user).data}
            )
        except Exception as exc:
            return self._handle_exception(exc, "update_me")

    # -------------------------------------------------------
    # Invite User
    # -------------------------------------------------------
    @extend_schema(
        tags=["Users"],
        summary="Invite a new or existing user",
        request=InviteUserSerializer,
    )
    @action(detail=False, methods=["post"], url_path="invite")
    @transaction.atomic                 
    def invite(self, request):
        try:
            serializer = InviteUserSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            inviter = request.user
            company = inviter.company

            if not company:
                return api_response(400, "failure", {}, "NO_COMPANY", "Inviter must belong to a company")

            # Check seat limits based on subscription
            from app.platform.subscriptions.models import Subscriptions
            subscription = (
                Subscriptions.objects
                .filter(companyId=company.companyId, status=Subscriptions.StatusChoices.ACTIVE)
                .order_by("-created_date")
                .first()
            )

            if subscription:
                # Count active users (seats used)
                active_users_count = User.objects.filter(
                    company=company,
                    status=User.Status.ACTIVE
                ).count()
                
                # Count pending invites
                pending_users_count = User.objects.filter(
                    company=company,
                    status=User.Status.PENDING
                ).count()
                
                total_seats_used = active_users_count + pending_users_count
                
                if total_seats_used >= subscription.license_count:
                    return api_response(
                        403, "failure", {},
                        "SEAT_LIMIT_REACHED",
                        f"Seat limit reached ({subscription.license_count} seats). Please upgrade your plan to invite more users."
                    )

            email = data["email"].lower()

            # disallow self-invite
            if email == inviter.email.lower():
                return api_response(400, "failure", {}, "CANNOT_INVITE_SELF", "You cannot invite yourself.")

            user = User.objects.filter(email__iexact=email).first()

            if not user:
                # new user
                user = User.objects.create(
                    email=email,
                    first_name=data.get("first_name", ""),
                    last_name=data.get("last_name", ""),
                    role=data.get("role", User.Role.USER),
                    status=User.Status.PENDING,
                    company=company,
                )
                user.set_unusable_password()
                user.save()

            else:
                # limit hijacking: block if other company
                if user.company and user.company != company:
                    return api_response(400, "failure", {}, "WRONG_COMPANY", "User belongs to another company")

                # update role + company
                user.company = company
                user.role = data.get("role", user.role)
                user.status = User.Status.PENDING
                user.save()

            # new invite token (delete old)
            InviteToken.objects.filter(user=user).delete()
            invite = InviteToken.create_for_user(user)

            frontend_url = settings.FRONTEND_BASE
            invite_link = f"{frontend_url}/auth/set-password?token={invite.token}"

            # best effort email send
            try:
                send_mail(
                    f"You're invited to {company.name}",
                    f"Click to join: {invite_link}",
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                )
            except Exception:
                logger.exception("Failed to send invite email")

            # Return seat information
            seat_info = {}
            if subscription:
                active_count = User.objects.filter(company=company, status=User.Status.ACTIVE).count()
                pending_count = User.objects.filter(company=company, status=User.Status.PENDING).count()
                seat_info = {
                    "seats_used": active_count + pending_count,
                    "seats_available": max(0, subscription.license_count - (active_count + pending_count)),
                    "seats_total": subscription.license_count,
                }

            return api_response(
                200, "success",
                {
                    "user": MiniUserSerializer(user).data,
                    "invite_token": str(invite.token),
                    "seat_info": seat_info,
                }
            )
        except Exception as exc:
            return self._handle_exception(exc, "invite")

    # -------------------------------------------------------
    # Accept Invite
    # -------------------------------------------------------
    @extend_schema(
        tags=["Users"],
        summary="Accept invite and set password",
        request=AcceptInviteSerializer,
    )
    @action(detail=False, methods=["post"], url_path="accept-invite")
    @transaction.atomic
    def accept_invite(self, request):
        try:
            serializer = AcceptInviteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # delegate logic to serializer
            user = serializer.save()

            return api_response(
                200, "success",
                {"user": MiniUserSerializer(user).data}
            )

        except Exception as exc:
            return self._handle_exception(exc, "accept_invite")

    # -------------------------------------------------------
    # Update User (admin/team action)
    # -------------------------------------------------------
    @extend_schema(tags=["Users"], summary="Update team member")
    @action(detail=True, methods=["put"], url_path="update")
    @transaction.atomic
    def update_user(self, request, pk=None):
        try:
            user = User.objects.filter(userId=pk).first()
            if not user:
                return api_response(404, "failure", {}, "NOT_FOUND", "User not found")

            if user.company != request.user.company:
                return api_response(403, "failure", {}, "NOT_YOUR_COMPANY", "Cannot update user outside your company")

            serializer = TeamMemberUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            for key, value in serializer.validated_data.items():
                setattr(user, key, value)

            user.last_updated_date = timezone.now()
            user.save()

            return api_response(200, "success", {"user": MiniUserSerializer(user).data})
        except Exception as exc:
            return self._handle_exception(exc, "update_user")

    # -------------------------------------------------------
    # Remove user (soft or hard delete)
    # -------------------------------------------------------
    @extend_schema(tags=["Users"], summary="Remove a team member")
    @action(detail=True, methods=["delete"], url_path="remove")
    @transaction.atomic
    def remove_user(self, request, pk=None):
        try:
            user = User.objects.filter(userId=pk).first()
            if not user:
                return api_response(404, "failure", {}, "NOT_FOUND", "User not found")

            if user.company != request.user.company:
                return api_response(403, "failure", {}, "NOT_YOUR_COMPANY", "Cannot remove user outside your company")

            if user.userId == request.user.userId:
                return api_response(400, "failure", {}, "CANNOT_REMOVE_SELF", "Cannot remove yourself")

            user.delete()

            return api_response(200, "success", {"message": "User removed"})
        except Exception as exc:
            return self._handle_exception(exc, "remove_user")

    # -------------------------------------------------------
    # Forgot Password
    # -------------------------------------------------------
    @extend_schema(tags=["Auth"], summary="Request password reset")
    @action(detail=False, methods=["post"], url_path="forgot-password")
    def forgot_password(self, request):
        """Send password reset email to user."""
        try:
            email = request.data.get("email", "").lower().strip()
            if not email:
                return api_response(400, "failure", {}, "EMAIL_REQUIRED", "Email is required")

            user = User.objects.filter(email__iexact=email).first()
            
            # Don't reveal if email exists (security best practice)
            if user and user.status == User.Status.ACTIVE:
                # Create password reset token
                reset_token = PasswordResetToken.create_for_user(
                    user, hours_valid=1
                )
                reset_token.ip_address = self._get_client_ip(request)
                reset_token.save(update_fields=["ip_address"])

                # Send reset email
                try:
                    frontend_url = settings.FRONTEND_BASE
                    reset_link = f"{frontend_url}/auth/reset-password?token={reset_token.token}"
                    send_mail(
                        "Reset your password",
                        f"Click to reset: {reset_link}\n\nThis link expires in 1 hour.",
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                    )
                except Exception:
                    logger.exception("Failed to send password reset email")

            # Always return success to prevent email enumeration
            return api_response(
                200, "success",
                {"message": "If the email exists, a password reset link has been sent."}
            )

        except Exception as exc:
            return self._handle_exception(exc, "forgot_password")

    # -------------------------------------------------------
    # Reset Password
    # -------------------------------------------------------
    @extend_schema(tags=["Auth"], summary="Reset password with token")
    @action(detail=False, methods=["post"], url_path="reset-password")
    def reset_password(self, request):
        """Reset password using token from email."""
        try:
            from app.platform.accounts.serializers import PasswordResetSerializer
            
            serializer = PasswordResetSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            token = serializer.validated_data["token"]
            new_password = serializer.validated_data["password"]

            reset_token = PasswordResetToken.objects.filter(token=token).first()
            if not reset_token or not reset_token.is_valid():
                return api_response(
                    400, "failure", {},
                    "INVALID_TOKEN",
                    "Invalid or expired password reset token."
                )

            user = reset_token.user
            user.set_password(new_password)
            user.last_password_change = timezone.now()
            user.unlock_account()  # Unlock if locked
            user.save(update_fields=["password", "last_password_change"])

            reset_token.mark_used()

            return api_response(200, "success", {"message": "Password reset successfully"})

        except Exception as exc:
            return self._handle_exception(exc, "reset_password")

    # -------------------------------------------------------
    # Verify Email
    # -------------------------------------------------------
    @extend_schema(tags=["Auth"], summary="Verify email address")
    @action(detail=False, methods=["post"], url_path="verify-email")
    def verify_email(self, request):
        """Verify email address using token."""
        try:
            token = request.data.get("token")
            if not token:
                return api_response(400, "failure", {}, "TOKEN_REQUIRED", "Token is required")

            verification_token = EmailVerificationToken.objects.filter(token=token).first()
            if not verification_token or not verification_token.is_valid():
                return api_response(
                    400, "failure", {},
                    "INVALID_TOKEN",
                    "Invalid or expired verification token."
                )

            user = verification_token.user
            user.email_verified = True
            user.email_verified_at = timezone.now()
            user.save(update_fields=["email_verified", "email_verified_at"])

            verification_token.mark_used()

            return api_response(200, "success", {"message": "Email verified successfully"})

        except Exception as exc:
            return self._handle_exception(exc, "verify_email")

    # -------------------------------------------------------
    # Resend Verification Email
    # -------------------------------------------------------
    @extend_schema(tags=["Auth"], summary="Resend email verification")
    @action(detail=False, methods=["post"], url_path="resend-verification")
    def resend_verification(self, request):
        """Resend email verification link."""
        try:
            if not request.user.is_authenticated:
                email = request.data.get("email", "").lower().strip()
                if not email:
                    return api_response(400, "failure", {}, "EMAIL_REQUIRED", "Email is required")
                user = User.objects.filter(email__iexact=email).first()
            else:
                user = request.user

            if not user:
                return api_response(404, "failure", {}, "USER_NOT_FOUND", "User not found")

            if user.email_verified:
                return api_response(400, "failure", {}, "ALREADY_VERIFIED", "Email already verified")

            # Create new verification token
            EmailVerificationToken.objects.filter(user=user).delete()
            verification_token = EmailVerificationToken.create_for_user(user, hours_valid=24)

            # Send verification email
            try:
                frontend_url = settings.FRONTEND_BASE
                verify_link = f"{frontend_url}/auth/verify-email?token={verification_token.token}"
                send_mail(
                    "Verify your email address",
                    f"Click to verify: {verify_link}",
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                )
            except Exception:
                logger.exception("Failed to send verification email")

            return api_response(200, "success", {"message": "Verification email sent"})

        except Exception as exc:
            return self._handle_exception(exc, "resend_verification")

    # -------------------------------------------------------
    # Helper: Get client IP
    # -------------------------------------------------------
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
