# app/onboarding/companies/urls.py
from django.urls import path

from app.onboarding.companies import (
    setup_company,
    update_company,
    team_members,
    update_modules,
    update_subscription,
    activate_setup,
    update_discount,
)

urlpatterns = [
    # setup
    path("setup/", setup_company.CompanySetupAPIView.as_view(), name="company-setup"),

    # company settings
    path("<uuid:companyId>/settings/", update_company.CompanySettingsAPIView.as_view(), name="company-settings"),

    # team members
    path("<uuid:companyId>/team/", team_members.TeamMemberAddAPIView.as_view(), name="company-team-add"),
    path("<uuid:companyId>/team/<uuid:userId>/", team_members.TeamMemberUpdateAPIView.as_view(), name="company-team-update"),
    path("<uuid:companyId>/team/<uuid:userId>/delete/", team_members.TeamMemberDeleteAPIView.as_view(), name="company-team-delete"),

    # modules
    path("<uuid:companyId>/modules/", update_modules.CompanyModulesUpdateAPIView.as_view(), name="company-modules-update"),

    # subscription
    path("<uuid:companyId>/subscription/", update_subscription.CompanySubscriptionUpdateAPIView.as_view(), name="company-subscription-update"),

    # activate
    path("<uuid:companyId>/activate/", activate_setup.CompanyActivateAPIView.as_view(), name="company-activate"),

    # discount (platform admin)
    path("<uuid:companyId>/discount/", update_discount.CompanyDiscountUpdateAPIView.as_view(), name="company-discount-update"),
]
