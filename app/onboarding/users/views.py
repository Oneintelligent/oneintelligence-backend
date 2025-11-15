import logging
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import authenticate
from rest_framework import permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse

from .models import User
from .serializers import (
    SignUpSerializer,
    SignInSerializer,
    UserWithCompanySerializer,
    UserProfileUpdateSerializer,
)
from app.utils.response import api_response  # your standard response helper

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

    # ---------- helpers ----------
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

    # ---------------------------
    # Signup
    # ---------------------------
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
            access = str(refresh.access_token)

            user.last_login_date = timezone.now()
            user.save(update_fields=["last_login_date"])

            payload = {"user": UserWithCompanySerializer(user).data, "access": access}
            res = api_response(status_code=200, status="success", data=payload)
            self._set_refresh_cookie(res, str(refresh))
            return res
        except Exception as exc:
            return self._handle_exception(exc, where="signup")

    # ---------------------------
    # Signin
    # ---------------------------
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
                    error_message="Invalid email or password.",
                )

            if getattr(user, "status", "").lower() != "active":
                return api_response(
                    status_code=status.HTTP_403_FORBIDDEN,
                    status="failure",
                    data={},
                    error_code="INACTIVE_ACCOUNT",
                    error_message="This account is inactive.",
                )

            refresh = RefreshToken.for_user(user)
            access = str(refresh.access_token)

            user.last_login_date = timezone.now()
            user.save(update_fields=["last_login_date"])

            payload = {"user": UserWithCompanySerializer(user).data, "access": access}
            res = api_response(status_code=200, status="success", data=payload)
            self._set_refresh_cookie(res, str(refresh))
            return res
        except Exception as exc:
            return self._handle_exception(exc, where="signin")

    # ---------------------------
    # Signout
    # ---------------------------
    @extend_schema(tags=["User Authentication"], summary="Sign out (clear refresh cookie)")
    @action(detail=False, methods=["post"], url_path="signout")
    def signout(self, request):
        try:
            res = api_response(status_code=200, status="success", data={"message": "Signed out"})
            cookie_name = settings.SIMPLE_JWT.get("AUTH_COOKIE", "oi_refresh_token")
            cookie_path = settings.SIMPLE_JWT.get("AUTH_COOKIE_PATH", "/")
            res.delete_cookie(key=cookie_name, path=cookie_path)
            return res
        except Exception as exc:
            return self._handle_exception(exc, where="signout")

    # ---------------------------
    # Token refresh (cookie)
    # ---------------------------
    @extend_schema(tags=["Tokens"], summary="Refresh access token (HttpOnly cookie)", responses={200: OpenApiResponse(description="New access token")})
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
                    error_code="MISSING_REFRESH_COOKIE",
                    error_message="Refresh cookie missing.",
                )

            try:
                old_refresh = RefreshToken(refresh_token)
            except TokenError as e:
                return api_response(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    status="failure",
                    data={},
                    error_code="INVALID_REFRESH",
                    error_message="Invalid refresh token.",
                )

            user_id_claim = settings.SIMPLE_JWT.get("USER_ID_CLAIM", "user_id")
            user_id = old_refresh.payload.get(user_id_claim)
            if not user_id:
                return api_response(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    status="failure",
                    data={},
                    error_code="INVALID_TOKEN",
                    error_message="Could not extract user_id from token.",
                )

            user = User.objects.filter(userId=user_id).first()
            if not user:
                return api_response(status_code=status.HTTP_404_NOT_FOUND, status="failure", data={}, error_code="USER_NOT_FOUND", error_message="User not found.")

            new_refresh = RefreshToken.for_user(user)
            new_access = str(new_refresh.access_token)

            res = api_response(status_code=200, status="success", data={"access": new_access})
            self._set_refresh_cookie(res, str(new_refresh))
            return res
        except Exception as exc:
            return self._handle_exception(exc, where="token_refresh")

    # ---------------------------
    # Get current user (me)
    # ---------------------------
    @extend_schema(
        tags=["Users"],
        summary="Get current authenticated user (with company)",
        responses={200: UserWithCompanySerializer},
    )
    @action(detail=False, methods=["get"], url_path="me")
    def get_me(self, request):
        try:
            user = request.user
            # ensure company is prefetched if available
            user = User.objects.select_related("company").filter(userId=user.userId).first() or user
            return api_response(status_code=200, status="success", data=UserWithCompanySerializer(user).data)
        except Exception as exc:
            return self._handle_exception(exc, where="get_me")

    # ---------------------------
    # Update current user (me)
    # ---------------------------
    @extend_schema(tags=["Users"], summary="Update current user", request=UserProfileUpdateSerializer)
    @action(detail=False, methods=["put"], url_path="me/update")
    def update_me(self, request):
        try:
            serializer = UserProfileUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user = request.user
            for k, v in serializer.validated_data.items():
                setattr(user, k, v)
            user.last_updated_date = timezone.now()
            user.save()

            return api_response(status_code=200, status="success", data={"message": "Profile updated", "user": UserWithCompanySerializer(user).data})
        except Exception as exc:
            return self._handle_exception(exc, where="update_me")


# app/onboarding/users/views.py

import logging
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import InviteToken, User
from .serializers import (
    InviteUserSerializer,
    AcceptInviteSerializer,
    MiniUserForTeamSerializer,
    TeamMemberUpdateSerializer,
)
from app.utils.response import api_response
from app.onboarding.companies.models import Company

logger = logging.getLogger(__name__)

@extend_schema(tags=["Users"])
class UsersAOIViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def _handle_exception(self, exc, where=""):
        logger.exception("%s: %s", where, str(exc))
        return api_response(500, "failure", {}, "SERVER_ERROR", str(exc))

    # -----------------------------------------
    # Invite a team member (Admin or company admin)
    # POST /users/invite/
    # -----------------------------------------
    @extend_schema(
        summary="Invite a team member",
        request=InviteUserSerializer,
        responses={200: OpenApiResponse(description="Invite created")},
    )
    @action(detail=False, methods=["post"], url_path="invite")
    @transaction.atomic
    def invite(self, request):
        try:
            # Only authenticated users can invite — you may want to check role
            serializer = InviteUserSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            # require company context — inviter's company
            inviter = request.user
            company = inviter.company
            if not company:
                return api_response(400, "failure", {}, "NO_COMPANY", "Inviter must belong to a company")

            # If user exists but inactive/pending, reuse user object; else create
            user = User.objects.filter(email__iexact=data["email"]).first()
            created = False
            if not user:
                user = User.objects.create(
                    email=data["email"],
                    first_name=data.get("first_name", ""),
                    last_name=data.get("last_name", ""),
                    role=data.get("role", User.Role.USER),
                    status=User.Status.PENDING,
                    company=company,
                )
                user.set_unusable_password()
                user.save()
                created = True
            else:
                # update company and role if necessary, mark pending if no password
                user.company = company
                user.role = data.get("role", user.role)
                user.status = User.Status.PENDING
                user.set_unusable_password()
                user.save()

            # create invite token (one-per-user)
            InviteToken.objects.filter(user=user).delete()
            invite = InviteToken.create_for_user(user)

            # build invite link (frontend route)
            frontend_base = getattr(settings, "FRONTEND_BASE", "http://localhost:3000")
            invite_url = f"{frontend_base}/auth/set-password?token={invite.token}"

            # send email (basic)
            subject = f"Invitation to join {company.name} on OneIntelligence"
            message = f"Hi {user.first_name or ''},\n\nYou were invited to join {company.name} on OneIntelligence. Click the link to set your password and finish setup:\n\n{invite_url}\n\nThis link expires on {invite.expires_at}.\n\nIf you weren't expecting this, you can ignore this email."
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [user.email]
            try:
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
            except Exception:
                logger.exception("Failed to send invite email")

            return api_response(200, "success", {"user": MiniUserForTeamSerializer(user).data, "invite_token": str(invite.token)})
        except Exception as exc:
            return self._handle_exception(exc, "invite")

    # -----------------------------------------
    # Accept invite / set password
    # POST /users/accept-invite/
    # -----------------------------------------
    @extend_schema(summary="Accept invite and set password", request=AcceptInviteSerializer)
    @action(detail=False, methods=["post"], url_path="accept-invite")
    @transaction.atomic
    def accept_invite(self, request):
        try:
            serializer = AcceptInviteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            token = serializer.validated_data["token"]
            raw_pwd = serializer.validated_data["password"]

            invite = InviteToken.objects.filter(token=token).select_related("user").first()
            if not invite or not invite.is_valid():
                return api_response(400, "failure", {}, "INVALID_TOKEN", "Invite token is invalid or expired")

            user = invite.user
            user.password = make_password(raw_pwd)
            user.status = User.Status.ACTIVE
            user.last_login_date = timezone.now()
            user.save(update_fields=["password", "status", "last_login_date"])

            # remove invite token
            invite.delete()

            # Optionally auto-login: return access token (use your existing JWT pattern)
            # For simplicity, return user data
            return api_response(200, "success", {"user": MiniUserForTeamSerializer(user).data})
        except Exception as exc:
            return self._handle_exception(exc, "accept_invite")

    # -----------------------------------------
    # Update user (role/status/name)
    # PUT /users/<userId>/update/
    # -----------------------------------------
    @extend_schema(summary="Update team member", request=TeamMemberUpdateSerializer)
    @action(detail=True, methods=["put"], url_path="update")
    @transaction.atomic
    def update_user(self, request, pk=None):
        try:
            user = User.objects.filter(userId=pk).first()
            if not user:
                return api_response(404, "failure", {}, "NOT_FOUND", "User not found")

            serializer = TeamMemberUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            for k, v in serializer.validated_data.items():
                setattr(user, k, v)
            user.last_updated_date = timezone.now()
            user.save()
            return api_response(200, "success", {"user": MiniUserForTeamSerializer(user).data})
        except Exception as exc:
            return self._handle_exception(exc, "update_user")

    # -----------------------------------------
    # Remove user (soft delete or hard) — here we delete
    # DELETE /users/<userId>/remove/
    # -----------------------------------------
    @extend_schema(summary="Remove team member")
    @action(detail=True, methods=["delete"], url_path="remove")
    @transaction.atomic
    def remove_user(self, request, pk=None):
        try:
            user = User.objects.filter(userId=pk).first()
            if not user:
                return api_response(404, "failure", {}, "NOT_FOUND", "User not found")

            # Prevent removing yourself (optional)
            if request.user.userId == user.userId:
                return api_response(400, "failure", {}, "CANNOT_REMOVE_SELF", "Cannot remove yourself")

            user.delete()
            return api_response(200, "success", {"message": "User removed"})
        except Exception as exc:
            return self._handle_exception(exc, "remove_user")
