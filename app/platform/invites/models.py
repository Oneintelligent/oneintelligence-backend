# app/onboarding/invites/models.py
import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta


def default_expiry():
    return timezone.now() + timedelta(days=7)


class InviteToken(models.Model):
    token = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invited_user_email = models.EmailField()
    invited_user_id = models.UUIDField(blank=True, null=True)  # may be linked to User.userId later
    inviter_user_id = models.UUIDField(blank=True, null=True)
    companyId = models.UUIDField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(default=default_expiry)
    used = models.BooleanField(default=False)

    class Meta:
        db_table = "invite_tokens"

    def is_valid(self):
        return (not self.used) and (self.expires_at >= timezone.now())

    def mark_used(self):
        self.used = True
        self.save(update_fields=["used"])
