import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

class Team(models.Model):
    """
    Universal team used across Sales, Support, Projects, Accounts.
    """
    team_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="teams",
        db_column="companyId"
    )

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="teams_created",
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "teams_team"
        ordering = ["name"]
        unique_together = ("company", "name")

    def __str__(self):
        return self.name
