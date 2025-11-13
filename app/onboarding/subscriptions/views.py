from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny
from .models import Subscriptions, SubscriptionPlan
from .serializers import SubscriptionsSerializer, SubscriptionPlanSerializer
from app.utils.response import api_response


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all().order_by("id")
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [AllowAny]

    # CREATE
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                status_code=status.HTTP_201_CREATED,
                data=serializer.data
            )
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            status="error",
            error_code="VALIDATION_ERROR",
            error_message=serializer.errors
        )

    # LIST
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            status_code=status.HTTP_200_OK,
            data=serializer.data
        )

    # RETRIEVE
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            status_code=status.HTTP_200_OK,
            data=serializer.data
        )

    # UPDATE
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                status_code=status.HTTP_200_OK,
                data=serializer.data
            )
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            status="error",
            error_code="VALIDATION_ERROR",
            error_message=serializer.errors
        )

    # DELETE
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return api_response(
            status_code=status.HTTP_200_OK,
            data={"message": "Deleted successfully"}
        )



class SubscriptionsViewSet(viewsets.ModelViewSet):
    queryset = Subscriptions.objects.all().order_by("-created_date")
    serializer_class = SubscriptionsSerializer
    permission_classes = [AllowAny]

    # CREATE
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            subscription = serializer.save()
            return api_response(
                status_code=status.HTTP_201_CREATED,
                data=self.get_serializer(subscription).data
            )
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            status="error",
            error_code="VALIDATION_ERROR",
            error_message=serializer.errors
        )

    # LIST
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            status_code=status.HTTP_200_OK,
            data=serializer.data
        )

    # RETRIEVE
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            status_code=status.HTTP_200_OK,
            data=serializer.data
        )

    # UPDATE
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                status_code=status.HTTP_200_OK,
                data=serializer.data
            )
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            status="error",
            error_code="VALIDATION_ERROR",
            error_message=serializer.errors
        )

    # DELETE
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return api_response(
            status_code=status.HTTP_200_OK,
            data={"message": "Deleted successfully"}
        )
