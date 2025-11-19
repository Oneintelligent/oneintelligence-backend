from django.urls import path
from companies.views import (
    CompanyCreateAPIView,
    CompanyRetrieveAPIView,
    CompanyUpdateAPIView,
)

urlpatterns = [
    path("", CompanyCreateAPIView.as_view(), name="company-create"),
    path("<uuid:companyId>/", CompanyRetrieveAPIView.as_view(), name="company-get"),
    path("<uuid:companyId>/update/", CompanyUpdateAPIView.as_view(), name="company-update"),
]
