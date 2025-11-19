from rest_framework.routers import DefaultRouter

from .views import SeatBucketViewSet, CompanyLicenseViewSet

router = DefaultRouter()
router.register(r"licensing/seat-buckets", SeatBucketViewSet, basename="seat-buckets")
router.register(r"licensing/company-licenses", CompanyLicenseViewSet, basename="company-licenses")

urlpatterns = router.urls

