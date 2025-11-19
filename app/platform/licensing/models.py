"""Company licensing and seat tracking (placeholder)."""
from django.db import models

from app.core.models import CoreBaseModel


class SeatBucket(CoreBaseModel):
    """Defines allowable seat packs for plans."""

    plan_code = models.CharField(max_length=32)
    seats = models.PositiveIntegerField()
    price = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "platform_licensing_seat_buckets"
        unique_together = ("plan_code", "seats")


class CompanyLicense(CoreBaseModel):
    """Tracks allocated and consumed seats per company."""

    company_id = models.UUIDField()
    plan_code = models.CharField(max_length=32)
    seat_bucket = models.ForeignKey(SeatBucket, on_delete=models.PROTECT, related_name="company_licenses")
    seats_purchased = models.PositiveIntegerField(default=1)
    seats_used = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "platform_licensing_company_licenses"
        indexes = [models.Index(fields=["company_id", "plan_code"])]

