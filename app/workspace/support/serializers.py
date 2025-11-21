# app/workspace/support/serializers.py
from rest_framework import serializers
from .models import Ticket, TicketComment, TicketAttachment
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


# ---------------------------------------------------------
# User Reference Serializer
# ---------------------------------------------------------
class UserRefSerializer(serializers.Serializer):
    userId = serializers.UUIDField()
    email = serializers.CharField(required=False)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)


# ---------------------------------------------------------
# Account Reference Serializer
# ---------------------------------------------------------
class AccountRefSerializer(serializers.Serializer):
    account_id = serializers.UUIDField()
    name = serializers.CharField(required=False)
    primary_email = serializers.EmailField(required=False)


# ---------------------------------------------------------
# Project Reference Serializer
# ---------------------------------------------------------
class ProjectRefSerializer(serializers.Serializer):
    project_id = serializers.UUIDField()
    name = serializers.CharField(required=False)
    status = serializers.CharField(required=False)


# ---------------------------------------------------------
# Task Reference Serializer
# ---------------------------------------------------------
class TaskRefSerializer(serializers.Serializer):
    task_id = serializers.UUIDField()
    title = serializers.CharField(required=False)
    status = serializers.CharField(required=False)


# ---------------------------------------------------------
# Team Reference Serializer
# ---------------------------------------------------------
class TeamRefSerializer(serializers.Serializer):
    team_id = serializers.UUIDField()
    name = serializers.CharField(required=False)


# ---------------------------------------------------------
# Ticket Attachment Serializer
# ---------------------------------------------------------
class TicketAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.SerializerMethodField()
    uploaded_by_id = serializers.UUIDField(write_only=True, required=False)
    ticket_id = serializers.SerializerMethodField()
    comment_id = serializers.SerializerMethodField()

    class Meta:
        model = TicketAttachment
        fields = (
            "attachment_id", "ticket_id", "comment_id", "file_name", "file_size",
            "file_type", "file_url", "file_path", "uploaded_by", "uploaded_by_id",
            "created_at"
        )
        read_only_fields = ("attachment_id", "created_at", "ticket_id", "comment_id")

    def get_ticket_id(self, obj):
        """Get ticket ID."""
        return str(obj.ticket.ticket_id) if obj.ticket else None

    def get_comment_id(self, obj):
        """Get comment ID."""
        return str(obj.comment.comment_id) if obj.comment else None

    def get_uploaded_by(self, obj):
        """Get uploaded_by reference."""
        if obj.uploaded_by:
            return UserRefSerializer({
                "userId": obj.uploaded_by.userId,
                "email": obj.uploaded_by.email,
                "first_name": obj.uploaded_by.first_name,
                "last_name": obj.uploaded_by.last_name
            }).data
        return None


# ---------------------------------------------------------
# Ticket Comment Serializer
# ---------------------------------------------------------
class TicketCommentSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    author_id = serializers.UUIDField(write_only=True, required=False)
    file_attachments = TicketAttachmentSerializer(many=True, read_only=True)
    attachments = serializers.JSONField(read_only=True, help_text="Legacy JSON field for attachment references")
    ticket_id = serializers.SerializerMethodField()

    class Meta:
        model = TicketComment
        fields = (
            "comment_id", "ticket_id", "author", "author_id", "content",
            "is_internal", "is_public", "attachments", "file_attachments", "created_at", "updated_at"
        )
        read_only_fields = ("comment_id", "created_at", "updated_at", "ticket_id")

    def get_ticket_id(self, obj):
        """Get ticket ID."""
        return str(obj.ticket.ticket_id) if obj.ticket else None

    def get_author(self, obj):
        """Get author reference."""
        if obj.author:
            return UserRefSerializer({
                "userId": obj.author.userId,
                "email": obj.author.email,
                "first_name": obj.author.first_name,
                "last_name": obj.author.last_name
            }).data
        return None


# ---------------------------------------------------------
# Ticket Serializer
# ---------------------------------------------------------
class TicketSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    owner_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    assignee = serializers.SerializerMethodField()
    assignee_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    account = serializers.SerializerMethodField()
    account_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    project = serializers.SerializerMethodField()
    project_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    task = serializers.SerializerMethodField()
    task_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    team = serializers.SerializerMethodField()
    team_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    created_by = serializers.SerializerMethodField()
    created_by_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    comments = TicketCommentSerializer(many=True, read_only=True)
    attachments = TicketAttachmentSerializer(many=True, read_only=True)
    
    is_overdue = serializers.BooleanField(read_only=True)
    comments_count = serializers.SerializerMethodField()
    unread_comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = "__all__"
        read_only_fields = (
            "ticket_id", "company", "created_by", "created_at", "updated_at", "first_response_at",
            "resolved_at", "closed_at", "first_response_time", "resolution_time"
        )

    def get_owner(self, obj):
        """Get owner reference."""
        if obj.owner:
            return UserRefSerializer({
                "userId": obj.owner.userId,
                "email": obj.owner.email,
                "first_name": obj.owner.first_name,
                "last_name": obj.owner.last_name
            }).data
        return None

    def get_assignee(self, obj):
        """Get assignee reference."""
        if obj.assignee:
            return UserRefSerializer({
                "userId": obj.assignee.userId,
                "email": obj.assignee.email,
                "first_name": obj.assignee.first_name,
                "last_name": obj.assignee.last_name
            }).data
        return None

    def get_account(self, obj):
        """Get account reference."""
        if obj.account:
            return AccountRefSerializer({
                "account_id": obj.account.account_id,
                "name": obj.account.name,
                "primary_email": obj.account.primary_email
            }).data
        return None

    def get_project(self, obj):
        """Get project reference."""
        if obj.project:
            return ProjectRefSerializer({
                "project_id": obj.project.project_id,
                "name": obj.project.name,
                "status": obj.project.status
            }).data
        return None

    def get_task(self, obj):
        """Get task reference."""
        if obj.task:
            return TaskRefSerializer({
                "task_id": obj.task.task_id,
                "title": obj.task.title,
                "status": obj.task.status
            }).data
        return None

    def get_team(self, obj):
        """Get team reference."""
        if obj.team:
            return TeamRefSerializer({
                "team_id": obj.team.team_id,
                "name": obj.team.name
            }).data
        return None

    def get_created_by(self, obj):
        """Get created_by reference."""
        if obj.created_by:
            return UserRefSerializer({
                "userId": obj.created_by.userId,
                "email": obj.created_by.email,
                "first_name": obj.created_by.first_name,
                "last_name": obj.created_by.last_name
            }).data
        return None

    def get_comments_count(self, obj):
        """Get total comments count for this ticket."""
        return obj.comments.filter(is_public=True).count()

    def get_unread_comments_count(self, obj):
        """Get unread comments count (for future implementation)."""
        # TODO: Implement unread tracking
        return 0

    def create(self, validated_data):
        account_id = validated_data.pop("account_id", None)
        project_id = validated_data.pop("project_id", None)
        task_id = validated_data.pop("task_id", None)
        owner_id = validated_data.pop("owner_id", None)
        assignee_id = validated_data.pop("assignee_id", None)
        team_id = validated_data.pop("team_id", None)
        created_by_id = validated_data.pop("created_by_id", None)
        
        # Set relationships if provided
        if account_id:
            try:
                from app.workspace.sales.models import Account
                validated_data["account"] = Account.objects.get(account_id=account_id, company_id=validated_data.get("company_id"))
            except Exception:
                pass
        
        if project_id:
            try:
                from app.workspace.projects.models import Project
                validated_data["project"] = Project.objects.get(project_id=project_id, company_id=validated_data.get("company_id"))
            except Exception:
                pass
        
        if task_id:
            try:
                from app.workspace.tasks.models import Task
                validated_data["task"] = Task.objects.get(task_id=task_id, company_id=validated_data.get("company_id"))
            except Exception:
                pass
        
        if owner_id:
            try:
                validated_data["owner"] = User.objects.get(userId=owner_id, company_id=validated_data.get("company_id"))
            except Exception:
                pass
        
        if assignee_id:
            try:
                validated_data["assignee"] = User.objects.get(userId=assignee_id, company_id=validated_data.get("company_id"))
            except Exception:
                pass
        
        if team_id:
            try:
                from app.platform.teams.models import Team
                validated_data["team"] = Team.objects.get(team_id=team_id, company_id=validated_data.get("company_id"))
            except Exception:
                pass
        
        if created_by_id:
            try:
                validated_data["created_by"] = User.objects.get(userId=created_by_id, company_id=validated_data.get("company_id"))
            except Exception:
                pass
        
        ticket = Ticket.objects.create(**validated_data)
        return ticket

    def update(self, instance, validated_data):
        account_id = validated_data.pop("account_id", None)
        project_id = validated_data.pop("project_id", None)
        task_id = validated_data.pop("task_id", None)
        owner_id = validated_data.pop("owner_id", None)
        assignee_id = validated_data.pop("assignee_id", None)
        team_id = validated_data.pop("team_id", None)
        
        # Update relationships if provided
        if account_id is not None:
            if account_id:
                try:
                    from app.workspace.sales.models import Account
                    instance.account = Account.objects.get(account_id=account_id, company_id=instance.company_id)
                except Exception:
                    instance.account = None
            else:
                instance.account = None
        
        if project_id is not None:
            if project_id:
                try:
                    from app.workspace.projects.models import Project
                    instance.project = Project.objects.get(project_id=project_id, company_id=instance.company_id)
                except Exception:
                    instance.project = None
            else:
                instance.project = None
        
        if task_id is not None:
            if task_id:
                try:
                    from app.workspace.tasks.models import Task
                    instance.task = Task.objects.get(task_id=task_id, company_id=instance.company_id)
                except Exception:
                    instance.task = None
            else:
                instance.task = None
        
        if owner_id is not None:
            if owner_id:
                try:
                    instance.owner = User.objects.get(userId=owner_id, company_id=instance.company_id)
                except Exception:
                    instance.owner = None
            else:
                instance.owner = None
        
        if assignee_id is not None:
            if assignee_id:
                try:
                    instance.assignee = User.objects.get(userId=assignee_id, company_id=instance.company_id)
                except Exception:
                    instance.assignee = None
            else:
                instance.assignee = None
        
        if team_id is not None:
            if team_id:
                try:
                    from app.platform.teams.models import Team
                    instance.team = Team.objects.get(team_id=team_id, company_id=instance.company_id)
                except Exception:
                    instance.team = None
            else:
                instance.team = None
        
        # Track status changes for SLA
        old_status = instance.status
        new_status = validated_data.get("status", old_status)
        
        if new_status == "open" and old_status == "new" and not instance.first_response_at:
            from django.utils import timezone
            instance.first_response_at = timezone.now()
            if instance.created_at:
                delta = timezone.now() - instance.created_at
                instance.first_response_time = int(delta.total_seconds() / 60)
        
        if new_status == "resolved" and old_status != "resolved" and not instance.resolved_at:
            from django.utils import timezone
            instance.resolved_at = timezone.now()
            if instance.created_at:
                delta = timezone.now() - instance.created_at
                instance.resolution_time = int(delta.total_seconds() / 60)
        
        if new_status == "closed" and old_status != "closed" and not instance.closed_at:
            from django.utils import timezone
            instance.closed_at = timezone.now()
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

