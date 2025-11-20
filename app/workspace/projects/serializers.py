# app/workspace/projects/serializers.py
from rest_framework import serializers
from .models import Project, ProjectMember
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
# Project Member Serializer
# ---------------------------------------------------------
class ProjectMemberSerializer(serializers.ModelSerializer):
    user = UserRefSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = ProjectMember
        fields = ("member_id", "user", "user_id", "role", "added_at", "added_by")
        read_only_fields = ("member_id", "added_at", "added_by")


# ---------------------------------------------------------
# Project Serializer
# ---------------------------------------------------------
class ProjectSerializer(serializers.ModelSerializer):
    owner = UserRefSerializer(read_only=True)
    owner_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    team = TeamRefSerializer(read_only=True)
    team_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    members = ProjectMemberSerializer(many=True, read_only=True)
    member_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    members_with_roles = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        write_only=True,
        required=False,
        help_text="List of members with roles: [{'user_id': 'uuid', 'role': 'owner|manager|member|viewer'}]"
    )
    
    is_overdue = serializers.BooleanField(read_only=True)
    tasks_count = serializers.SerializerMethodField()
    completed_tasks_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = "__all__"
        read_only_fields = ("project_id", "created_at", "updated_at", "health_score", "completed_date")

    def get_tasks_count(self, obj):
        """Get total tasks count for this project."""
        try:
            from app.workspace.tasks.models import Task
            return Task.objects.filter(project=obj).count()
        except:
            return 0

    def get_completed_tasks_count(self, obj):
        """Get completed tasks count for this project."""
        try:
            from app.workspace.tasks.models import Task
            return Task.objects.filter(project=obj, status="completed").count()
        except:
            return 0

    def create(self, validated_data):
        member_ids = validated_data.pop("member_ids", [])
        members_with_roles = validated_data.pop("members_with_roles", [])
        team_id = validated_data.pop("team_id", None)
        owner_id = validated_data.pop("owner_id", None)
        
        # Set owner if provided
        if owner_id:
            try:
                validated_data["owner"] = User.objects.get(userId=owner_id)
            except User.DoesNotExist:
                pass
        
        # Create project
        project = super().create(validated_data)
        
        # Set team if provided
        if team_id:
            try:
                project.team = Team.objects.get(team_id=team_id, company=project.company)
                project.save()
            except Team.DoesNotExist:
                pass
        
        # Add members with roles (preferred method)
        if members_with_roles:
            request = self.context.get("request")
            added_by = request.user if request else None
            for member_data in members_with_roles:
                user_id = member_data.get("user_id")
                role = member_data.get("role", "member")
                if user_id:
                    try:
                        user = User.objects.get(userId=user_id, company=project.company)
                        ProjectMember.objects.get_or_create(
                            project=project,
                            user=user,
                            defaults={"role": role, "added_by": added_by}
                        )
                    except User.DoesNotExist:
                        pass
        # Fallback to member_ids (for backward compatibility)
        elif member_ids:
            request = self.context.get("request")
            added_by = request.user if request else None
            for user_id in member_ids:
                try:
                    user = User.objects.get(userId=user_id, company=project.company)
                    ProjectMember.objects.get_or_create(
                        project=project,
                        user=user,
                        defaults={"role": "member", "added_by": added_by}
                    )
                except User.DoesNotExist:
                    pass
        
        return project

    def update(self, instance, validated_data):
        member_ids = validated_data.pop("member_ids", None)
        members_with_roles = validated_data.pop("members_with_roles", None)
        team_id = validated_data.pop("team_id", None)
        owner_id = validated_data.pop("owner_id", None)
        
        # Update owner if provided
        if owner_id is not None:
            if owner_id:
                try:
                    instance.owner = User.objects.get(userId=owner_id)
                except User.DoesNotExist:
                    instance.owner = None
            else:
                instance.owner = None
        
        # Update team if provided
        if team_id is not None:
            if team_id:
                try:
                    instance.team = Team.objects.get(team_id=team_id, company=instance.company)
                except Team.DoesNotExist:
                    instance.team = None
            else:
                instance.team = None
        
        # Update project
        instance = super().update(instance, validated_data)
        
        # Update members with roles (preferred method)
        if members_with_roles is not None:
            request = self.context.get("request")
            added_by = request.user if request else None
            
            # Get current member user IDs
            existing_member_user_ids = set(instance.members.values_list("user_id", flat=True))
            new_member_user_ids = {member_data.get("user_id") for member_data in members_with_roles if member_data.get("user_id")}
            
            # Remove members not in new list
            to_remove = existing_member_user_ids - new_member_user_ids
            if to_remove:
                instance.members.filter(user_id__in=to_remove).delete()
            
            # Add/update members
            for member_data in members_with_roles:
                user_id = member_data.get("user_id")
                role = member_data.get("role", "member")
                if user_id:
                    try:
                        user = User.objects.get(userId=user_id, company=instance.company)
                        member, created = ProjectMember.objects.get_or_create(
                            project=instance,
                            user=user,
                            defaults={"role": role, "added_by": added_by}
                        )
                        if not created:
                            # Update role if member already exists
                            member.role = role
                            member.save()
                    except User.DoesNotExist:
                        pass
        # Fallback to member_ids (for backward compatibility)
        elif member_ids is not None:
            # Remove existing members not in new list
            existing_member_ids = set(instance.members.values_list("user_id", flat=True))
            new_member_ids = set(member_ids)
            to_remove = existing_member_ids - new_member_ids
            to_add = new_member_ids - existing_member_ids
            
            if to_remove:
                instance.members.filter(user_id__in=to_remove).delete()
            
            # Add new members
            request = self.context.get("request")
            added_by = request.user if request else None
            for user_id in to_add:
                try:
                    user = User.objects.get(userId=user_id, company=instance.company)
                    ProjectMember.objects.get_or_create(
                        project=instance,
                        user=user,
                        defaults={"role": "member", "added_by": added_by}
                    )
                except User.DoesNotExist:
                    pass
        
        # Update status to completed if progress is 100
        if instance.progress == 100 and instance.status != "completed":
            instance.status = "completed"
            from django.utils import timezone
            instance.completed_date = timezone.now()
            instance.save()
        
        return instance


# ---------------------------------------------------------
# Project Create Serializer (simplified)
# ---------------------------------------------------------
class ProjectCreateSerializer(serializers.ModelSerializer):
    owner_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    team_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    member_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    members_with_roles = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        write_only=True,
        required=False,
        help_text="List of members with roles: [{'user_id': 'uuid', 'role': 'owner|manager|member|viewer'}]"
    )

    class Meta:
        model = Project
        exclude = ("project_id", "company", "health_score", "created_at", "updated_at", "completed_date")
        extra_kwargs = {
            "shared_with": {"required": False},
            "visibility": {"required": False},
            "tags": {"required": False},
            "metadata": {"required": False},
        }

    def create(self, validated_data):
        member_ids = validated_data.pop("member_ids", [])
        members_with_roles = validated_data.pop("members_with_roles", [])
        team_id = validated_data.pop("team_id", None)
        owner_id = validated_data.pop("owner_id", None)
        
        # Set owner if provided
        if owner_id:
            try:
                validated_data["owner"] = User.objects.get(userId=owner_id)
            except User.DoesNotExist:
                pass
        
        # Create project
        project = super().create(validated_data)
        
        # Set team if provided
        if team_id:
            try:
                project.team = Team.objects.get(team_id=team_id, company=project.company)
                project.save()
            except Team.DoesNotExist:
                pass
        
        # Add members with roles (preferred method)
        if members_with_roles:
            request = self.context.get("request")
            added_by = request.user if request else None
            for member_data in members_with_roles:
                user_id = member_data.get("user_id")
                role = member_data.get("role", "member")
                if user_id:
                    try:
                        user = User.objects.get(userId=user_id, company=project.company)
                        ProjectMember.objects.get_or_create(
                            project=project,
                            user=user,
                            defaults={"role": role, "added_by": added_by}
                        )
                    except User.DoesNotExist:
                        pass
        # Fallback to member_ids (for backward compatibility)
        elif member_ids:
            request = self.context.get("request")
            added_by = request.user if request else None
            for user_id in member_ids:
                try:
                    user = User.objects.get(userId=user_id, company=project.company)
                    ProjectMember.objects.get_or_create(
                        project=project,
                        user=user,
                        defaults={"role": "member", "added_by": added_by}
                    )
                except User.DoesNotExist:
                    pass
        
        return project

