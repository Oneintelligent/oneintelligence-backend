# app/onboarding/invites/urls.py
from django.urls import path
from .views import InviteAcceptAPIView

urlpatterns = [
    path("accept/", InviteAcceptAPIView.as_view(), name="invite-accept"),
]
