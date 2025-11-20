"""
OneIntelligent AI Models
Database models for conversations, messages, and analytics
"""

from django.db import models
from django.contrib.auth import get_user_model
from app.core.models import CoreBaseModel, SoftDeleteModel

User = get_user_model()


class Conversation(CoreBaseModel, SoftDeleteModel):
    """
    Represents a conversation session with OneIntelligent AI.
    Each conversation has a title, mode, and belongs to a user.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ai_conversations",
        db_index=True
    )
    
    title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Auto-generated or user-provided conversation title"
    )
    
    mode = models.CharField(
        max_length=50,
        default="Advisor",
        choices=[
            ("Advisor", "Advisor"),
            ("Developer", "Developer"),
            ("Researcher", "Researcher"),
            ("Learner", "Learner"),
            ("Sales", "Sales"),
            ("Marketing", "Marketing"),
            ("Customer Support", "Customer Support"),
            ("Task Manager", "Task Manager"),
        ],
        db_index=True
    )
    
    # Metadata
    message_count = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    last_activity_at = models.DateTimeField(auto_now=True, db_index=True)
    
    class Meta:
        db_table = "ai_conversations"
        ordering = ["-last_activity_at"]
        indexes = [
            models.Index(fields=["user", "-last_activity_at"]),
            models.Index(fields=["user", "mode"]),
        ]
    
    def __str__(self):
        return f"{self.title or 'Untitled'} ({self.user.email})"


class Message(CoreBaseModel):
    """
    Represents a single message in a conversation.
    Stores both user and assistant messages with metadata.
    """
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        db_index=True
    )
    
    role = models.CharField(
        max_length=20,
        choices=[
            ("user", "User"),
            ("assistant", "Assistant"),
            ("system", "System"),
        ],
        db_index=True
    )
    
    content = models.TextField(
        help_text="Message content (text, markdown, etc.)"
    )
    
    # Metadata
    tokens_used = models.IntegerField(
        default=0,
        help_text="Number of tokens used for this message"
    )
    
    model_used = models.CharField(
        max_length=100,
        blank=True,
        help_text="AI model used to generate this message"
    )
    
    finish_reason = models.CharField(
        max_length=50,
        blank=True,
        help_text="Reason for completion (stop, length, etc.)"
    )
    
    # Error tracking
    has_error = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    
    # Ordering
    sequence = models.IntegerField(
        default=0,
        help_text="Message order in conversation",
        db_index=True
    )
    
    class Meta:
        db_table = "ai_messages"
        ordering = ["conversation", "sequence", "created_at"]
        indexes = [
            models.Index(fields=["conversation", "sequence"]),
            models.Index(fields=["conversation", "role"]),
        ]
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class ConversationAnalytics(CoreBaseModel):
    """
    Analytics and insights for AI conversations.
    Tracks usage patterns, token consumption, and user engagement.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ai_analytics",
        db_index=True
    )
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="analytics",
        null=True,
        blank=True
    )
    
    # Usage metrics
    total_messages = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0.0,
        help_text="Estimated cost in USD"
    )
    
    # Engagement metrics
    avg_response_time = models.FloatField(
        default=0.0,
        help_text="Average response time in seconds"
    )
    
    # Mode usage
    mode_used = models.CharField(max_length=50, blank=True)
    
    # Date tracking
    date = models.DateField(
        auto_now_add=True,
        db_index=True,
        help_text="Date for daily aggregation"
    )
    
    class Meta:
        db_table = "ai_conversation_analytics"
        unique_together = [["user", "date", "mode_used"]]
        indexes = [
            models.Index(fields=["user", "-date"]),
            models.Index(fields=["date", "mode_used"]),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.date} ({self.total_tokens} tokens)"


class UserPreferences(CoreBaseModel):
    """
    User preferences for AI interactions.
    Stores default modes, settings, and personalization.
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="ai_preferences"
    )
    
    default_mode = models.CharField(
        max_length=50,
        default="Advisor",
        choices=Conversation._meta.get_field("mode").choices
    )
    
    # UI preferences
    auto_scroll = models.BooleanField(default=True)
    show_timestamps = models.BooleanField(default=True)
    compact_mode = models.BooleanField(default=False)
    
    # AI preferences
    temperature = models.FloatField(
        default=0.7,
        help_text="Default temperature for AI responses"
    )
    
    max_tokens = models.IntegerField(
        default=2000,
        help_text="Default max tokens per response"
    )
    
    # Learning preferences
    enable_suggestions = models.BooleanField(default=True)
    enable_action_extraction = models.BooleanField(default=True)
    enable_follow_ups = models.BooleanField(default=True)
    
    class Meta:
        db_table = "ai_user_preferences"
    
    def __str__(self):
        return f"Preferences for {self.user.email}"
