# app/onboarding/companies/team_members.py
import logging
from django.db import transaction
from rest_framework import status, permissions
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from app.utils.response import api_response
from app.onboarding.companies.models import Company
from app.onboarding.companies.serializers import TeamMemberSerializer
from app.onboarding.users.models import User
from app.onboarding.invites.utils import create_invite, send_invite_email
from app.onboarding.invites.serializers import InviteTokenSerializer
from app.onboarding.companies.permissions import is_owner, is_company_admin

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Team"],
    summary="Add a team member (invite or attach existing user)",
    description="Owner or Admins can add team members. If user exists without a password an invite is sent.",
    request=TeamMemberSerializer,
    responses={201: OpenApiResponse(description="Member added")}
)
class TeamMemberAddAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, companyId):
        serializer = TeamMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        company = Company.objects.filter(companyId=companyId).first()
        if not company:
            return api_response(status_code=status.HTTP_404_NOT_FOUND, status="error", data={}, error_code="NOT_FOUND", error_message="Company not found")

        if not (is_owner(request.user, company) or is_company_admin(request.user, company)):
            return api_response(status_code=status.HTTP_403_FORBIDDEN, status="error", data={}, error_code="FORBIDDEN", error_message="Not allowed to add users")

        email = data["email"].lower().strip()
        existing = User.objects.filter(email__iexact=email).first()
        invite_meta = None

        if existing:
            if existing.has_usable_password():
                existing.companyId = str(company.companyId)
                existing.role = data.get("role", existing.role)
                existing.status = User.Status.ACTIVE
                existing.save(update_fields=["companyId", "role", "status", "last_updated_date"])
                user_id = str(existing.userId)
            else:
                invite = create_invite(email=email, inviter_user_id=request.user.userId, companyId=company.companyId)
                invite_meta = send_invite_email(invite)
                user_id = str(existing.userId)
        else:
            user = User.objects.create(
                email=email,
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
                role=data.get("role", User.Role.USER),
                companyId=str(company.companyId),
                status=User.Status.INACTIVE,
            )
            user.set_unusable_password()
            user.save()
            invite = create_invite(email=email, inviter_user_id=request.user.userId, companyId=company.companyId)
            invite_meta = send_invite_email(invite)
            user_id = str(user.userId)

        ul = company.user_list or []
        if user_id not in ul:
            ul.append(user_id)
            company.user_list = ul
            company.save(update_fields=["user_list", "last_updated_date"])

        return api_response(status_code=status.HTTP_201_CREATED, status="success", data={"userId": user_id, "invite": invite_meta or {}})


@extend_schema(
    tags=["Team"],
    summary="Update a team member",
    request=TeamMemberSerializer,
    responses={200: OpenApiResponse(description="Member updated")},
)
class TeamMemberUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def put(self, request, companyId, userId):
        company = Company.objects.filter(companyId=companyId).first()
        if not company:
            return api_response(status_code=status.HTTP_404_NOT_FOUND, status="error", data={}, error_code="NOT_FOUND", error_message="Company not found")

        if not (is_owner(request.user, company) or is_company_admin(request.user, company)):
            return api_response(status_code=status.HTTP_403_FORBIDDEN, status="error", data={}, error_code="FORBIDDEN", error_message="Not allowed to update users")

        user = User.objects.filter(userId=userId).first()
        if not user or str(user.companyId) != str(company.companyId):
            return api_response(status_code=status.HTTP_404_NOT_FOUND, status="error", data={}, error_code="NOT_FOUND", error_message="User not found")

        allowed = ["first_name", "last_name", "role", "status", "phone", "profile_picture_url"]
        changed = False
        for k in allowed:
            if k in request.data:
                setattr(user, k, request.data[k])
                changed = True
        if changed:
            user.save(update_fields=[f for f in allowed if f in request.data] + ["last_updated_date"])

        return api_response(status_code=status.HTTP_200_OK, status="success", data={"updated": changed})


@extend_schema(
    tags=["Team"],
    summary="Remove a team member",
    responses={200: OpenApiResponse(description="Member removed")},
)
class TeamMemberDeleteAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def delete(self, request, companyId, userId):
        company = Company.objects.filter(companyId=companyId).first()
        if not company:
            return api_response(status_code=status.HTTP_404_NOT_FOUND, status="error", data={}, error_code="NOT_FOUND", error_message="Company not found")

        if not (is_owner(request.user, company) or is_company_admin(request.user, company)):
            return api_response(status_code=status.HTTP_403_FORBIDDEN, status="error", data={}, error_code="FORBIDDEN", error_message="Not allowed to remove users")

        user = User.objects.filter(userId=userId).first()
        if not user:
            return api_response(status_code=status.HTTP_404_NOT_FOUND, status="error", data={}, error_code="NOT_FOUND", error_message="User not found")

        if str(user.companyId) == str(company.companyId):
            user.companyId = None
            user.save(update_fields=["companyId", "last_updated_date"])

        ul = company.user_list or []
        if str(userId) in ul:
            ul = [u for u in ul if u != str(userId)]
            company.user_list = ul
            company.save(update_fields=["user_list", "last_updated_date"])

        return api_response(status_code=status.HTTP_200_OK, status="success", data={"removed": True})
