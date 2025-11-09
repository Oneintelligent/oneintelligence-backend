import logging
from rest_framework import viewsets
from .models import User
from app.onboarding.users.serializers import UserSerializer

from app.utils.response import api_response

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        """Create a user (no foreign key logic)."""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            return api_response(status_code=0, status="success", data=UserSerializer(user).data)
        except Exception as e:
            logger.exception("Error creating user")
            return api_response(status_code=1, status="failure", data={}, error_code="CREATE_USER_ERROR", error_message=str(e))

    def update(self, request, *args, **kwargs):
        """Full update."""
        try:
            serializer = self.get_serializer(self.get_object(), data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            return api_response(status_code=0, status="success", data=UserSerializer(user).data)
        except Exception as e:
            logger.exception("Error updating user")
            return api_response(status_code=1, status="failure", data={}, error_code="UPDATE_USER_ERROR", error_message=str(e))

    def partial_update(self, request, *args, **kwargs):
        """Partial update."""
        try:
            serializer = self.get_serializer(self.get_object(), data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            return api_response(status_code=0, status="success", data=UserSerializer(user).data)
        except Exception as e:
            logger.exception("Error partially updating user")
            return api_response(status_code=1, status="failure", data={}, error_code="PARTIAL_UPDATE_USER_ERROR", error_message=str(e))
