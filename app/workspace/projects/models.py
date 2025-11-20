import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings


# =========================================================
#  PROJECT MODEL
# =========================================================
class Project(models.Model):
    project_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        db_column="companyId",
        related_name="projects"
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="projects_owned"
    )

    team = models.ForeignKey(
        "teams.Team",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="projects"
    )

    # ----------- Core Fields ----------
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    STATUS_CHOICES = [
        ("planning", "Planning"),
        ("active", "Active"),
        ("on_hold", "On Hold"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planning")
    
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium")

    # ----------- Dates ----------
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)

    # ----------- Progress ----------
    progress = models.IntegerField(default=0)  # 0-100 percentage

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

    # ----------- AI / Intelligent Fields ----------
    health_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True)

    # ----------- Audit ----------
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workspace_projects"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["owner"]),
            models.Index(fields=["team"]),
            models.Index(fields=["due_date"]),
        ]

    def __str__(self):
        return self.name or "Unnamed Project"

    @property
    def is_overdue(self):
        """Check if project is overdue."""
        if self.due_date and self.status not in ["completed", "cancelled"]:
            from django.utils import timezone
            return timezone.now().date() > self.due_date
        return False


# =========================================================
#  PROJECT MEMBER MODEL
# =========================================================
class ProjectMember(models.Model):
    member_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="members",
        db_column="projectId"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_memberships"
    )

    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("manager", "Manager"),
        ("member", "Member"),
        ("viewer", "Viewer"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")

    # ----------- Audit ----------
    added_at = models.DateTimeField(default=timezone.now)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_members_added"
    )

    class Meta:
        db_table = "workspace_project_members"
        unique_together = [("project", "user")]
        indexes = [
            models.Index(fields=["project"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.project.name}"

