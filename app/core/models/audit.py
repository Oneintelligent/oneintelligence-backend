"""Audit logging primitives."""
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from .base import CoreBaseModel


class AuditLog(CoreBaseModel):
    """Tracks important user actions across modules."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    company_id = models.UUIDField(null=True, blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True)
    object_id = models.UUIDField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    action = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "core_audit_logs"
        indexes = [
            models.Index(fields=["company_id", "action"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        ts = self.created_at.astimezone(timezone.utc) if self.created_at else ""
        actor = getattr(self.actor, "email", "system")
        return f"[{ts}] {actor} -> {self.action}"
