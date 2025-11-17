import logging
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import authenticate
from rest_framework import permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse

from django.core.mail import send_mail

from app.onboarding.users.models import User, InviteToken
from app.onboarding.users.serializers import (
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

logger = logging.getLogger(__name__)



@extend_schema_view(
    list=extend_schema(exclude=True),
    retrieve=extend_schema(exclude=True),
    update=extend_schema(exclude=True),
    partial_update=extend_schema(exclude=True),
    destroy=extend_schema(exclude=True),
)
class AOIViewSet(viewsets.ViewSet):
    """
    Action-Oriented ViewSet for user auth and profile.
    """

    def get_permissions(self):
        open_actions = ["signup", "signin", "token_refresh"]
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
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            status="failure",
            data={},
            error_code="SERVER_ERROR",
            error_message=str(exc),
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

            refresh = RefreshToken.for_user(user)
            access = str(refresh.access_token)

            # refresh last_login
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])

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

            # username=<email>
            user = authenticate(request=request, username=email, password=password)

            if not user:
                return api_response(
                    401, "failure", {},
                    "INVALID_CREDENTIALS",
                    "Invalid email or password."
                )

            if user.status != User.Status.ACTIVE:
                return api_response(
                    403, "failure", {},
                    "INACTIVE_ACCOUNT",
                    "This account is inactive."
                )

            refresh = RefreshToken.for_user(user)
            access = str(refresh.access_token)

            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])

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

            user_id = old.payload.get("user_id")
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

            return api_response(
                200, "success",
                {"message": "Profile updated", "user": UserWithCompanySerializer(user).data}
            )
        except Exception as exc:
            return self._handle_exception(exc, "update_me")

    # -------------------------------------------------------
    # Invite User
    # -------------------------------------------------------
    @extend_schema(tags=["Users"], summary="Invite a new or existing user")
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

            return api_response(
                200, "success",
                {"user": MiniUserSerializer(user).data, "invite_token": str(invite.token)}
            )
        except Exception as exc:
            return self._handle_exception(exc, "invite")

    # -------------------------------------------------------
    # Accept Invite
    # -------------------------------------------------------
    @extend_schema(tags=["Users"], summary="Accept invite and set password")
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
