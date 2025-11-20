# app/workspace/projects/views.py
import logging
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Project, ProjectMember
from .serializers import (
    ProjectSerializer, ProjectCreateSerializer, ProjectMemberSerializer
)
from .permissions import can_view_project, can_edit_project, can_delete_project
from app.utils.response import api_response

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(exclude=False),
    retrieve=extend_schema(exclude=False),
    create=extend_schema(exclude=False),
    update=extend_schema(exclude=False),
    partial_update=extend_schema(exclude=False),
    destroy=extend_schema(exclude=False),
)
class ProjectViewSet(viewsets.ViewSet):
    """
    Projects — Action-Oriented Interface (AOI) ViewSet
    """
    permission_classes = [IsAuthenticated]

    def _handle_exception(self, exc: Exception, where: str = ""):
        logger.exception("%s: %s", where, str(exc))
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            status="failure",
            data={},
            error_code="SERVER_ERROR",
            error_message=str(exc),
        )

    @extend_schema(tags=["Projects"], summary="List projects (scoped to user)")
    def list(self, request):
        try:
            user = request.user
            qs = Project.objects.filter(company_id=user.company_id).select_related("owner", "team")

            # Filter by visibility and membership
            conditions = Q(owner_id=user.userId) | Q(members__user=user)
            conditions = conditions | Q(visibility="company")
            if user.team_id:
                conditions = conditions | Q(team_id=user.team_id, visibility="team")
            if Q(visibility="shared", shared_with__contains=[str(user.userId)]):
                conditions = conditions | Q(visibility="shared", shared_with__contains=[str(user.userId)])
            
            qs = qs.filter(conditions).distinct()

            # Search
            qtext = request.query_params.get("q")
            if qtext:
                qs = qs.filter(Q(name__icontains=qtext) | Q(description__icontains=qtext))

            # Filter by status
            status_filter = request.query_params.get("status")
            if status_filter:
                qs = qs.filter(status=status_filter)

            # Filter by priority
            priority_filter = request.query_params.get("priority")
            if priority_filter:
                qs = qs.filter(priority=priority_filter)

            # Order by
            order_by = request.query_params.get("order_by", "-updated_at")
            qs = qs.order_by(order_by)

            # Annotate with task counts
            qs = qs.annotate(
                tasks_count=Count("tasks", distinct=True),
                completed_tasks_count=Count("tasks", filter=Q(tasks__status="completed"), distinct=True)
            )

            serializer = ProjectSerializer(qs, many=True, context={"request": request})
            return api_response(200, "success", serializer.data)

        except Exception as exc:
            return self._handle_exception(exc, "ProjectViewSet.list")

    @extend_schema(tags=["Projects"], summary="Retrieve a project")
    def retrieve(self, request, pk=None):
        try:
            project = get_object_or_404(Project.objects.select_related("owner", "team"), project_id=pk)
            if not can_view_project(request.user, project):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have access to this project")
            
            serializer = ProjectSerializer(project, context={"request": request})
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "ProjectViewSet.retrieve")

    @extend_schema(tags=["Projects"], summary="Create a project", request=ProjectCreateSerializer)
    @transaction.atomic
    def create(self, request):
        try:
            serializer = ProjectCreateSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            project = serializer.save(company_id=request.user.company_id, owner=request.user)
            return api_response(201, "success", ProjectSerializer(project, context={"request": request}).data)
        except Exception as exc:
            return self._handle_exception(exc, "ProjectViewSet.create")

    @extend_schema(tags=["Projects"], summary="Update a project", request=ProjectSerializer)
    @transaction.atomic
    def update(self, request, pk=None):
        try:
            project = get_object_or_404(Project, project_id=pk)
            if not can_edit_project(request.user, project):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have permission to edit this project")
            
            serializer = ProjectSerializer(project, data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "ProjectViewSet.update")

    @extend_schema(tags=["Projects"], summary="Partially update a project", request=ProjectSerializer)
    @transaction.atomic
    def partial_update(self, request, pk=None):
        try:
            project = get_object_or_404(Project, project_id=pk)
            if not can_edit_project(request.user, project):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have permission to edit this project")
            
            serializer = ProjectSerializer(project, data=request.data, partial=True, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "ProjectViewSet.partial_update")

    @extend_schema(tags=["Projects"], summary="Delete a project")
    @transaction.atomic
    def destroy(self, request, pk=None):
        try:
            project = get_object_or_404(Project, project_id=pk)
            if not can_delete_project(request.user, project):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have permission to delete this project")
            project.delete()
            return api_response(200, "success", {"message": "Project deleted"})
        except Exception as exc:
            return self._handle_exception(exc, "ProjectViewSet.destroy")

    @extend_schema(tags=["Projects"], summary="Get project tasks")
    @action(detail=True, methods=["get"])
    def tasks(self, request, pk=None):
        try:
            project = get_object_or_404(Project, project_id=pk)
            if not can_view_project(request.user, project):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have access to this project")
            
            try:
                from app.workspace.tasks.models import Task
                from app.workspace.tasks.serializers import TaskSerializer
                tasks = Task.objects.filter(project=project).select_related("owner", "assignee")
                serializer = TaskSerializer(tasks, many=True, context={"request": request})
                return api_response(200, "success", serializer.data)
            except ImportError:
                return api_response(200, "success", [])
        except Exception as exc:
            return self._handle_exception(exc, "ProjectViewSet.tasks")

    @extend_schema(tags=["Projects"], summary="Get project team members")
    @action(detail=True, methods=["get"])
    def team(self, request, pk=None):
        try:
            project = get_object_or_404(Project, project_id=pk)
            if not can_view_project(request.user, project):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have access to this project")
            
            members = project.members.select_related("user", "added_by")
            serializer = ProjectMemberSerializer(members, many=True)
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "ProjectViewSet.team")

