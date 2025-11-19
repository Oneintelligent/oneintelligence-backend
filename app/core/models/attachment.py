"""Attachment model shared across modules."""
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .base import CoreBaseModel


class Attachment(CoreBaseModel):
    """Stores metadata for uploaded files and links them via GenericForeignKey."""

    company_id = models.UUIDField(null=True, blank=True)
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="attachments",
    )

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey("content_type", "object_id")

    filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=128, blank=True)
    storage_key = models.CharField(max_length=512)
    size_bytes = models.BigIntegerField(default=0)

    extra_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "core_attachments"
        indexes = [
            models.Index(fields=["company_id"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return self.filename
