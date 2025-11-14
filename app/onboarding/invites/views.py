# app/onboarding/invites/views.py
import logging
from rest_framework.views import APIView
from rest_framework import status, permissions
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse

from app.onboarding.invites.models import InviteToken
from app.onboarding.invites.serializers import InviteAcceptSerializer
from app.onboarding.users.models import User
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
                # create new user
                user = User.objects.create(
                    email=email,
                    first_name="",
                    last_name="",
                    companyId=str(invite.companyId) if invite.companyId else None,
                    status=User.Status.ACTIVE,
                    role=User.Role.USER
                )
                created = True

            # set password and activate
            user.set_password(password)
            user.status = User.Status.ACTIVE
            if invite.companyId and not user.companyId:
                user.companyId = str(invite.companyId)
            user.last_login_date = timezone.now()
            user.save(update_fields=["password", "status", "companyId", "last_login_date", "last_updated_date"])

            invite.mark_used()

            # create tokens
            refresh = RefreshToken()
            refresh["user_id"] = str(user.userId)
            refresh["email"] = user.email
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
