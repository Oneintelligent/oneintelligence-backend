import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings


# =========================================================
#  TICKET MODEL
# =========================================================
class Ticket(models.Model):
    ticket_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        db_column="companyId",
        related_name="support_tickets"
    )

    # ----------- Relationships ----------
    account = models.ForeignKey(
        "sales.Account",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets",
        db_column="accountId"
    )

    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets",
        db_column="projectId"
    )

    task = models.ForeignKey(
        "tasks.Task",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets",
        db_column="taskId"
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets_owned",
        db_column="ownerId"
    )

    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets_assigned",
        db_column="assigneeId"
    )

    team = models.ForeignKey(
        "teams.Team",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets"
    )

    # ----------- Core Fields ----------
    subject = models.CharField(max_length=500)
    description = models.TextField(blank=True, null=True)
    
    STATUS_CHOICES = [
        ("new", "New"),
        ("open", "Open"),
        ("pending", "Pending"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium")
    
    TYPE_CHOICES = [
        ("question", "Question"),
        ("problem", "Problem"),
        ("task", "Task"),
        ("feature", "Feature Request"),
        ("bug", "Bug Report"),
    ]
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="question")
    
    SOURCE_CHOICES = [
        ("email", "Email"),
        ("phone", "Phone"),
        ("web", "Web"),
        ("chat", "Chat"),
        ("api", "API"),
        ("social", "Social Media"),
    ]
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="web")

    # ----------- Customer Information ----------
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True)
    customer_phone = models.CharField(max_length=50, blank=True, null=True)

    # ----------- Dates & SLA ----------
    first_response_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    
    # SLA tracking (in minutes)
    first_response_sla = models.IntegerField(null=True, blank=True, help_text="First response SLA in minutes")
    resolution_sla = models.IntegerField(null=True, blank=True, help_text="Resolution SLA in minutes")
    first_response_time = models.IntegerField(null=True, blank=True, help_text="Actual first response time in minutes")
    resolution_time = models.IntegerField(null=True, blank=True, help_text="Actual resolution time in minutes")

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
    
    # Custom fields (for extensibility)
    custom_fields = models.JSONField(default=dict, blank=True)

    # ----------- AI / Intelligent Fields ----------
    sentiment_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    satisfaction_score = models.IntegerField(null=True, blank=True, help_text="Customer satisfaction rating 1-5")
    
    # ----------- Audit ----------
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets_created",
        db_column="createdById"
    )

    class Meta:
        db_table = "support_tickets"
        ordering = ["-updated_at"]
        indexes = [
            # Composite indexes for common query patterns (using field names, not db_column)
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "priority"]),
            models.Index(fields=["company", "updated_at"]),
            models.Index(fields=["company", "status", "updated_at"]),
            models.Index(fields=["company", "assignee"]),
            models.Index(fields=["company", "owner"]),
            models.Index(fields=["company", "created_by"]),
            # Single field indexes
            models.Index(fields=["assignee"]),
            models.Index(fields=["owner"]),
            models.Index(fields=["account"]),
            models.Index(fields=["project"]),
            models.Index(fields=["task"]),
            models.Index(fields=["customer_email"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["updated_at"]),
            models.Index(fields=["due_date"]),
            # Index for overdue queries
            models.Index(fields=["due_date", "status"]),
            # Index for visibility queries
            models.Index(fields=["visibility", "company"]),
        ]

    def __str__(self):
        return f"#{self.ticket_id.hex[:8]} - {self.subject}"

    @property
    def is_overdue(self):
        """Check if ticket is overdue."""
        if self.due_date and self.status not in ["resolved", "closed"]:
            return timezone.now() > self.due_date
        return False

    @property
    def is_sla_breached(self):
        """Check if SLA is breached."""
        if self.due_date and self.status not in ["resolved", "closed"]:
            return timezone.now() > self.due_date
        return False


# =========================================================
#  TICKET COMMENT MODEL
# =========================================================
class TicketComment(models.Model):
    comment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="comments",
        db_column="ticketId"
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_comments",
        db_column="authorId"
    )

    # Comment can be from internal user or customer
    is_internal = models.BooleanField(default=False, help_text="Internal note (not visible to customer)")
    is_public = models.BooleanField(default=True, help_text="Visible to customer")

    content = models.TextField()
    
    # Attachments reference (stored as JSON array of file IDs/URLs)
    attachments = models.JSONField(default=list, blank=True)

    # ----------- Audit ----------
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "support_ticket_comments"
        ordering = ["created_at"]
        indexes = [
            # Composite index for ticket + created_at (common query pattern)
            models.Index(fields=["ticket", "created_at"]),
            # Single field indexes
            models.Index(fields=["ticket"]),
            models.Index(fields=["author"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Comment on {self.ticket.subject}"


# =========================================================
#  TICKET ATTACHMENT MODEL
# =========================================================
class TicketAttachment(models.Model):
    attachment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="attachments",
        db_column="ticketId"
    )

    comment = models.ForeignKey(
        TicketComment,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="file_attachments",
        db_column="commentId"
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_attachments",
        db_column="uploadedById"
    )

    # File information
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField(help_text="File size in bytes")
    file_type = models.CharField(max_length=100, blank=True, null=True)
    file_url = models.URLField(max_length=500)
    file_path = models.CharField(max_length=500, blank=True, null=True)

    # ----------- Audit ----------
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "support_ticket_attachments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["ticket"]),
            models.Index(fields=["comment"]),
        ]

    def __str__(self):
        return f"{self.file_name} - {self.ticket.subject}"

