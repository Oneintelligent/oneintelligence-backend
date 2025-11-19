# app/onboarding/invites/views.py
import logging
from rest_framework.views import APIView
from rest_framework import status, permissions
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse

from app.platform.invites.models import InviteToken
from app.platform.invites.serializers import InviteAcceptSerializer
from app.platform.accounts.models import User
from app.utils.response import api_response

logger = logging.getLogger(__name__)

@extend_schema(
    tags=["Invites"],
    summary="Accept invitation",
    description="Accept an invite token, set password, activate user, mark invite used, return JWT tokens.",
    request=InviteAcceptSerializer
)
class InviteAcceptAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request):
        try:
            serializer = InviteAcceptSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            token_val = serializer.validated_data["token"]
            password = serializer.validated_data["password"]

            invite = InviteToken.objects.filter(token=token_val).first()
            if not invite:
                return api_response(status_code=status.HTTP_404_NOT_FOUND, status="error", error_code="INVITE_NOT_FOUND", error_message="Invite not found")

            if not invite.is_valid():
                return api_response(status_code=status.HTTP_400_BAD_REQUEST, status="error", error_code="INVITE_INVALID", error_message="Invite expired or used")

            email = invite.invited_user_email.lower().strip()

            user = User.objects.filter(email__iexact=email).first()
            created = False
            if not user:
                # Get company if invite has companyId
                company = None
                if invite.companyId:
                    from app.platform.companies.models import Company
                    company = Company.objects.filter(companyId=invite.companyId).first()
                
                # create new user
                user = User.objects.create(
                    email=email,
                    first_name="",
                    last_name="",
                    company=company,
                    status=User.Status.PENDING,  # Will be activated after password is set
                    role=User.Role.USER
                )
                created = True

            # set password and activate
            user.set_password(password)
            user.status = User.Status.ACTIVE
            # Link company if invite has one and user doesn't
            if invite.companyId and not user.company:
                from app.platform.companies.models import Company
                company = Company.objects.filter(companyId=invite.companyId).first()
                if company:
                    user.company = company
            user.last_login = timezone.now()
            user.save(update_fields=["password", "status", "company", "last_login", "last_updated_date"])

            invite.mark_used()

            # create tokens using for_user to ensure proper userId claim
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            data = {
                "userId": str(user.userId),
                "email": user.email,
                "access": access_token,
                "refresh": refresh_token,
                "created": created
            }
            return api_response(status_code=status.HTTP_200_OK, status="success", data=data)

        except Exception as e:
            logger.exception("Error accepting invite")
            return api_response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, status="error", error_code="INVITE_ACCEPT_ERROR", error_message=str(e))
