# app/onboarding/companies/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("setup/", views.CompanySetupAPIView.as_view(), name="company-setup"),
    path("<uuid:companyId>/settings/", views.CompanySettingsAPIView.as_view(), name="company-settings"),
    path("<uuid:companyId>/team/", views.TeamMemberAPIView.as_view(), name="company-team-add"),
    path("<uuid:companyId>/team/<uuid:userId>/", views.TeamMemberAPIView.as_view(), name="company-team-manage"),
    path("<uuid:companyId>/products/", views.CompanyProductsUpdateAPIView.as_view(), name="company-products"),
    path("<uuid:companyId>/subscription/", views.CompanySubscriptionUpdateAPIView.as_view(), name="company-subscription"),
    path("<uuid:companyId>/discount/", views.CompanyDiscountUpdateAPIView.as_view(), name="company-discount"),
]
