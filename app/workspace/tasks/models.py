import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings


# =========================================================
#  TASK MODEL
# =========================================================
class Task(models.Model):
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        db_column="companyId",
        related_name="tasks"
    )

    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks"
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks_owned"
    )

    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks_assigned",
        db_column="assigneeId"
    )

    team = models.ForeignKey(
        "teams.Team",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks"
    )

    # ----------- Core Fields ----------
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    STATUS_CHOICES = [
        ("todo", "To Do"),
        ("in_progress", "In Progress"),
        ("review", "Review"),
        ("done", "Done"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="todo")
    
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium")

    # ----------- Dates ----------
    due_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    started_date = models.DateTimeField(null=True, blank=True)

    # ----------- Visibility & Sharing ----------
    VISIBILITY_CHOICES = [
        ("owner", "Owner Only"),
        ("team", "Team"),
        ("company", "Company"),
        ("shared", "Shared"),
    ]
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default="team")
    shared_with = models.JSONField(default=list, blank=True)

    # ----------- Metadata ----------
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    # ----------- Estimates & Time Tracking ----------
    estimated_hours = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    actual_hours = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # ----------- Audit ----------
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workspace_tasks"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["project"]),
            models.Index(fields=["owner"]),
            models.Index(fields=["assignee"]),
            models.Index(fields=["team"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["priority", "status"]),
        ]

    def __str__(self):
        return self.title or "Unnamed Task"

    @property
    def is_overdue(self):
        """Check if task is overdue."""
        if self.due_date and self.status not in ["completed", "done", "cancelled"]:
            return timezone.now() > self.due_date
        return False

    def mark_completed(self):
        """Mark task as completed."""
        self.status = "completed"
        self.completed_date = timezone.now()
        self.save(update_fields=["status", "completed_date", "updated_at"])

