# app/workspace/tasks/views.py
import logging
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Task
from .serializers import (
    TaskSerializer, TaskCreateSerializer, BulkTaskUpdateSerializer
)
from .permissions import can_view_task, can_edit_task, can_delete_task, HasTaskPermission
from app.platform.rbac.mixins import RBACPermissionMixin
from app.platform.rbac.constants import Modules, Permissions
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
class TaskViewSet(viewsets.ViewSet, RBACPermissionMixin):
    """
    Tasks — Action-Oriented Interface (AOI) ViewSet
    Enterprise-grade RBAC integration
    """
    permission_classes = [IsAuthenticated]
    module = Modules.TASKS

    def _handle_exception(self, exc: Exception, where: str = ""):
        logger.exception("%s: %s", where, str(exc))
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            status="failure",
            data={},
            error_code="SERVER_ERROR",
            error_message=str(exc),
        )

    @extend_schema(tags=["Tasks"], summary="List tasks (scoped to user)")
    def list(self, request):
        try:
            user = request.user
            
            # Check permission using RBAC
            if not self.check_permission(user, Permissions.VIEW):
                return self.get_permission_denied_response("You don't have permission to view tasks")
            
            # Filter by permissions using RBAC mixin
            qs = Task.objects.filter(company_id=user.company_id).select_related("owner", "assignee", "project", "team")
            qs = self.filter_queryset_by_permissions(qs, user)

            # Search
            qtext = request.query_params.get("q")
            if qtext:
                qs = qs.filter(Q(title__icontains=qtext) | Q(description__icontains=qtext))

            # Filter by status
            status_filter = request.query_params.get("status")
            if status_filter:
                qs = qs.filter(status=status_filter)

            # Filter by priority
            priority_filter = request.query_params.get("priority")
            if priority_filter:
                qs = qs.filter(priority=priority_filter)

            # Filter by project
            project_id = request.query_params.get("project_id")
            if project_id:
                qs = qs.filter(project_id=project_id)

            # Filter by assignee
            assignee_id = request.query_params.get("assignee_id")
            if assignee_id:
                qs = qs.filter(assignee_id=assignee_id)

            # Filter by owner
            owner_id = request.query_params.get("owner_id")
            if owner_id:
                qs = qs.filter(owner_id=owner_id)

            # Filter overdue
            overdue = request.query_params.get("overdue")
            if overdue == "true":
                from django.utils import timezone
                qs = qs.filter(due_date__lt=timezone.now()).exclude(status__in=["completed", "done", "cancelled"])

            # Order by
            order_by = request.query_params.get("order_by", "-updated_at")
            qs = qs.order_by(order_by)

            serializer = TaskSerializer(qs, many=True, context={"request": request})
            return api_response(200, "success", serializer.data)

        except Exception as exc:
            return self._handle_exception(exc, "TaskViewSet.list")

    @extend_schema(tags=["Tasks"], summary="Retrieve a task")
    def retrieve(self, request, pk=None):
        try:
            task = get_object_or_404(Task.objects.select_related("owner", "assignee", "project", "team"), task_id=pk)
            if not can_view_task(request.user, task):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have access to this task")
            
            serializer = TaskSerializer(task, context={"request": request})
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "TaskViewSet.retrieve")

    @extend_schema(tags=["Tasks"], summary="Create a task", request=TaskCreateSerializer)
    @transaction.atomic
    def create(self, request):
        try:
            serializer = TaskCreateSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            task = serializer.save(company_id=request.user.company_id, owner=request.user)
            return api_response(201, "success", TaskSerializer(task, context={"request": request}).data)
        except Exception as exc:
            return self._handle_exception(exc, "TaskViewSet.create")

    @extend_schema(tags=["Tasks"], summary="Update a task", request=TaskSerializer)
    @transaction.atomic
    def update(self, request, pk=None):
        try:
            task = get_object_or_404(Task, task_id=pk)
            if not can_edit_task(request.user, task):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have permission to edit this task")
            
            serializer = TaskSerializer(task, data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "TaskViewSet.update")

    @extend_schema(tags=["Tasks"], summary="Partially update a task", request=TaskSerializer)
    @transaction.atomic
    def partial_update(self, request, pk=None):
        try:
            task = get_object_or_404(Task, task_id=pk)
            if not can_edit_task(request.user, task):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have permission to edit this task")
            
            serializer = TaskSerializer(task, data=request.data, partial=True, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "TaskViewSet.partial_update")

    @extend_schema(tags=["Tasks"], summary="Delete a task")
    @transaction.atomic
    def destroy(self, request, pk=None):
        try:
            task = get_object_or_404(Task, task_id=pk)
            if not can_delete_task(request.user, task):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have permission to delete this task")
            task.delete()
            return api_response(200, "success", {"message": "Task deleted"})
        except Exception as exc:
            return self._handle_exception(exc, "TaskViewSet.destroy")

    @extend_schema(tags=["Tasks"], summary="Update task status")
    @action(detail=True, methods=["put"])
    @transaction.atomic
    def status(self, request, pk=None):
        try:
            task = get_object_or_404(Task, task_id=pk)
            if not can_edit_task(request.user, task):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have permission to edit this task")
            
            new_status = request.data.get("status")
            if not new_status:
                return api_response(400, "failure", {}, "VALIDATION_ERROR", "Status is required")
            
            task.status = new_status
            if new_status in ["completed", "done"]:
                from django.utils import timezone
                task.completed_date = timezone.now()
            task.save()
            
            serializer = TaskSerializer(task, context={"request": request})
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "TaskViewSet.status")

    @extend_schema(tags=["Tasks"], summary="Bulk update tasks", request=BulkTaskUpdateSerializer)
    @action(detail=False, methods=["post"])
    @transaction.atomic
    def bulk_update(self, request):
        try:
            serializer = BulkTaskUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            task_ids = serializer.validated_data["task_ids"]
            tasks = Task.objects.filter(task_id__in=task_ids, company_id=request.user.company_id)
            
            # Check permissions
            for task in tasks:
                if not can_edit_task(request.user, task):
                    return api_response(403, "failure", {}, "FORBIDDEN", f"You don't have permission to edit task {task.task_id}")
            
            # Update fields
            update_fields = {}
            if "status" in serializer.validated_data:
                update_fields["status"] = serializer.validated_data["status"]
            if "priority" in serializer.validated_data:
                update_fields["priority"] = serializer.validated_data["priority"]
            if "assignee_id" in serializer.validated_data:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    assignee = User.objects.get(userId=serializer.validated_data["assignee_id"])
                    tasks.update(assignee=assignee)
                except User.DoesNotExist:
                    pass
            if "project_id" in serializer.validated_data:
                from app.workspace.projects.models import Project
                try:
                    project = Project.objects.get(project_id=serializer.validated_data["project_id"])
                    tasks.update(project=project)
                except Project.DoesNotExist:
                    pass
            if "tags" in serializer.validated_data:
                tasks.update(tags=serializer.validated_data["tags"])
            
            if update_fields:
                tasks.update(**update_fields)
            
            updated_tasks = Task.objects.filter(task_id__in=task_ids).select_related("owner", "assignee", "project")
            result_serializer = TaskSerializer(updated_tasks, many=True, context={"request": request})
            return api_response(200, "success", result_serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "TaskViewSet.bulk_update")

