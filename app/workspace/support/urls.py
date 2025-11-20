# app/workspace/support/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TicketViewSet, TicketCommentViewSet

router = DefaultRouter()
router.register(r"tickets", TicketViewSet, basename="tickets")
router.register(r"comments", TicketCommentViewSet, basename="ticket-comments")

urlpatterns = [
    path("", include(router.urls)),
]

