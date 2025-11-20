# app/workspace/tasks/serializers.py
from rest_framework import serializers
from .models import Task
from django.conf import settings
from django.contrib.auth import get_user_model
from app.platform.teams.models import Team

User = get_user_model()


# ---------------------------------------------------------
# User Reference Serializer
# ---------------------------------------------------------
class UserRefSerializer(serializers.Serializer):
    userId = serializers.UUIDField()
    email = serializers.CharField(required=False)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)


class TeamRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ("team_id", "name")


# ---------------------------------------------------------
# Project Reference Serializer
# ---------------------------------------------------------
class ProjectRefSerializer(serializers.Serializer):
    project_id = serializers.UUIDField()
    name = serializers.CharField(required=False)
    status = serializers.CharField(required=False)


# ---------------------------------------------------------
# Task Serializer
# ---------------------------------------------------------
class TaskSerializer(serializers.ModelSerializer):
    owner = UserRefSerializer(read_only=True)
    owner_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    assignee = UserRefSerializer(read_only=True)
    assignee_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    project = ProjectRefSerializer(read_only=True)
    project_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    team = TeamRefSerializer(read_only=True)
    team_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = "__all__"
        read_only_fields = ("task_id", "created_at", "updated_at", "completed_date", "started_date")

    def create(self, validated_data):
        project_id = validated_data.pop("project_id", None)
        team_id = validated_data.pop("team_id", None)
        owner_id = validated_data.pop("owner_id", None)
        assignee_id = validated_data.pop("assignee_id", None)
        
        # Set owner if provided
        if owner_id:
            try:
                validated_data["owner"] = User.objects.get(userId=owner_id)
            except User.DoesNotExist:
                pass
        
        # Set assignee if provided
        if assignee_id:
            try:
                validated_data["assignee"] = User.objects.get(userId=assignee_id)
            except User.DoesNotExist:
                pass
        
        # Create task
        task = super().create(validated_data)
        
        # Set project if provided
        if project_id:
            try:
                from app.workspace.projects.models import Project
                task.project = Project.objects.get(project_id=project_id, company=task.company)
                task.save()
            except:
                pass
        
        # Set team if provided
        if team_id:
            try:
                task.team = Team.objects.get(team_id=team_id, company=task.company)
                task.save()
            except Team.DoesNotExist:
                pass
        
        return task

    def update(self, instance, validated_data):
        project_id = validated_data.pop("project_id", None)
        team_id = validated_data.pop("team_id", None)
        owner_id = validated_data.pop("owner_id", None)
        assignee_id = validated_data.pop("assignee_id", None)
        
        # Update owner if provided
        if owner_id is not None:
            if owner_id:
                try:
                    instance.owner = User.objects.get(userId=owner_id)
                except User.DoesNotExist:
                    instance.owner = None
            else:
                instance.owner = None
        
        # Update assignee if provided
        if assignee_id is not None:
            if assignee_id:
                try:
                    instance.assignee = User.objects.get(userId=assignee_id)
                except User.DoesNotExist:
                    instance.assignee = None
            else:
                instance.assignee = None
        
        # Update project if provided
        if project_id is not None:
            if project_id:
                try:
                    from app.workspace.projects.models import Project
                    instance.project = Project.objects.get(project_id=project_id, company=instance.company)
                except:
                    instance.project = None
            else:
                instance.project = None
        
        # Update team if provided
        if team_id is not None:
            if team_id:
                try:
                    instance.team = Team.objects.get(team_id=team_id, company=instance.company)
                except Team.DoesNotExist:
                    instance.team = None
            else:
                instance.team = None
        
        # Update task
        instance = super().update(instance, validated_data)
        
        # Auto-update dates based on status
        if instance.status == "in_progress" and not instance.started_date:
            from django.utils import timezone
            instance.started_date = timezone.now()
            instance.save()
        
        if instance.status in ["completed", "done"] and not instance.completed_date:
            from django.utils import timezone
            instance.completed_date = timezone.now()
            instance.save()
        
        return instance


# ---------------------------------------------------------
# Task Create Serializer (simplified)
# ---------------------------------------------------------
class TaskCreateSerializer(serializers.ModelSerializer):
    project_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    team_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    assignee_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Task
        exclude = ("task_id", "company", "created_at", "updated_at", "completed_date", "started_date")
        extra_kwargs = {
            "shared_with": {"required": False},
            "visibility": {"required": False},
            "tags": {"required": False},
            "metadata": {"required": False},
        }


# ---------------------------------------------------------
# Bulk Task Update Serializer
# ---------------------------------------------------------
class BulkTaskUpdateSerializer(serializers.Serializer):
    task_ids = serializers.ListField(child=serializers.UUIDField())
    status = serializers.CharField(required=False)
    priority = serializers.CharField(required=False)
    assignee_id = serializers.UUIDField(required=False, allow_null=True)
    project_id = serializers.UUIDField(required=False, allow_null=True)
    tags = serializers.ListField(child=serializers.CharField(), required=False)

