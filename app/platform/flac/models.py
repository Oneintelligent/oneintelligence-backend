"""Field-Level Access Control models (placeholder)."""
from django.db import models

from app.core.models import CoreBaseModel


class RoleFieldPolicy(CoreBaseModel):
    """Stub model describing per-role field rules (to be expanded)."""

    company_id = models.UUIDField(null=True, blank=True)
    role = models.CharField(max_length=64)
    module = models.CharField(max_length=64)
    field = models.CharField(max_length=128)
    visibility = models.CharField(max_length=16, default="view")  # view | edit | hidden
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "platform_flac_role_field_policies"
        unique_together = ("company_id", "role", "module", "field")
