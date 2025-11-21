from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OnboardingViewSet
from .views_complete import CompleteOnboardingViewSet

router = DefaultRouter()
router.register(r"onboarding", OnboardingViewSet, basename="onboarding")
router.register(r"onboarding/complete", CompleteOnboardingViewSet, basename="complete-onboarding")

urlpatterns = [
    path("", include(router.urls)),
]

