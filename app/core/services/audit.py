"""Helper functions for writing audit logs."""
from typing import Optional, Mapping, Any

from django.contrib.contenttypes.models import ContentType

from app.core.models import AuditLog


def record_audit(*, actor=None, company_id=None, obj=None, action: str, description: str = "", metadata: Optional[Mapping[str, Any]] = None, ip_address: str = "", user_agent: str = "") -> AuditLog:
    metadata = dict(metadata or {})
    content_type = None
    object_id = None
    if obj is not None:
        content_type = ContentType.objects.get_for_model(obj.__class__)
        object_id = getattr(obj, "pk", None)
    return AuditLog.objects.create(
        actor=actor,
        company_id=company_id or getattr(actor, "company_id", None),
        content_type=content_type,
        object_id=object_id,
        action=action,
        description=description,
        metadata=metadata,
        ip_address=ip_address,
        user_agent=user_agent,
    )
