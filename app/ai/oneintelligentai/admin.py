from django.contrib import admin
from .models import Conversation, Message, ConversationAnalytics, UserPreferences


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'mode', 'message_count', 'total_tokens', 'last_activity_at', 'created_at']
    list_filter = ['mode', 'created_at', 'last_activity_at']
    search_fields = ['title', 'user__email', 'user__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-last_activity_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'role', 'sequence', 'tokens_used', 'model_used', 'has_error', 'created_at']
    list_filter = ['role', 'has_error', 'model_used', 'created_at']
    search_fields = ['content', 'conversation__title', 'conversation__user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(ConversationAnalytics)
class ConversationAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'mode_used', 'total_messages', 'total_tokens', 'total_cost', 'avg_response_time']
    list_filter = ['date', 'mode_used']
    search_fields = ['user__email', 'user__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-date', '-total_tokens']


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ['user', 'default_mode', 'temperature', 'max_tokens', 'enable_suggestions', 'enable_action_extraction']
    list_filter = ['default_mode', 'enable_suggestions', 'enable_action_extraction']
    search_fields = ['user__email', 'user__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
