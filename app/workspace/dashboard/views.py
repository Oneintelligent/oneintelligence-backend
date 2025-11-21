# app/workspace/dashboard/views.py
import logging
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from app.utils.response import api_response
from app.platform.rbac.mixins import RBACPermissionMixin
from app.platform.rbac.constants import Modules, Permissions
from app.platform.rbac.utils import has_module_permission, is_platform_admin

logger = logging.getLogger(__name__)


class DashboardViewSet(viewsets.ViewSet, RBACPermissionMixin):
    """
    Dashboard — Aggregated data endpoints
    Enterprise-grade RBAC integration
    """
    permission_classes = [IsAuthenticated]
    module = Modules.DASHBOARD

    def _handle_exception(self, exc: Exception, where: str = ""):
        logger.exception("%s: %s", where, str(exc))
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            status="failure",
            data={},
            error_code="SERVER_ERROR",
            error_message=str(exc),
        )

    @extend_schema(tags=["Dashboard"], summary="Get dashboard summary")
    @action(detail=False, methods=["get"])
    def summary(self, request):
        """
        Get aggregated dashboard data including:
        - Projects count and status breakdown
        - Tasks count and status breakdown
        - Sales metrics (leads, opportunities)
        - Recent activity
        """
        try:
            user = request.user
            
            # Check permission using RBAC
            if not self.check_permission(user, Permissions.VIEW_ANALYTICS):
                return self.get_permission_denied_response("You don't have permission to view dashboard analytics")
            
            company_id = user.company_id

            # Projects summary
            projects_data = {}
            try:
                from app.workspace.projects.models import Project
                projects_qs = Project.objects.filter(company_id=company_id)
                
                # Filter by visibility
                conditions = Q(owner_id=user.userId) | Q(members__user=user)
                conditions = conditions | Q(visibility="company")
                if user.team_id:
                    conditions = conditions | Q(team_id=user.team_id, visibility="team")
                conditions = conditions | Q(visibility="shared", shared_with__contains=[str(user.userId)])
                projects_qs = projects_qs.filter(conditions).distinct()
                
                projects_data = {
                    "total": projects_qs.count(),
                    "by_status": dict(projects_qs.values("status").annotate(count=Count("project_id")).values_list("status", "count")),
                    "overdue": projects_qs.filter(due_date__lt=timezone.now().date()).exclude(status__in=["completed", "cancelled"]).count(),
                }
            except Exception as e:
                logger.warning(f"Error fetching projects: {e}")
                projects_data = {"total": 0, "by_status": {}, "overdue": 0}

            # Tasks summary
            tasks_data = {}
            try:
                from app.workspace.tasks.models import Task
                tasks_qs = Task.objects.filter(company_id=company_id)
                
                # Filter by visibility
                conditions = Q(owner_id=user.userId) | Q(assignee_id=user.userId)
                conditions = conditions | Q(visibility="company")
                if user.team_id:
                    conditions = conditions | Q(team_id=user.team_id, visibility="team")
                conditions = conditions | Q(visibility="shared", shared_with__contains=[str(user.userId)])
                tasks_qs = tasks_qs.filter(conditions).distinct()
                
                tasks_data = {
                    "total": tasks_qs.count(),
                    "by_status": dict(tasks_qs.values("status").annotate(count=Count("task_id")).values_list("status", "count")),
                    "overdue": tasks_qs.filter(due_date__lt=timezone.now()).exclude(status__in=["completed", "done", "cancelled"]).count(),
                    "assigned_to_me": tasks_qs.filter(assignee_id=user.userId).exclude(status__in=["completed", "done"]).count(),
                }
            except Exception as e:
                logger.warning(f"Error fetching tasks: {e}")
                tasks_data = {"total": 0, "by_status": {}, "overdue": 0, "assigned_to_me": 0}

            # Sales summary
            sales_data = {}
            try:
                from app.workspace.sales.models import Lead, Opportunity
                
                # Leads
                leads_qs = Lead.objects.filter(company_id=company_id)
                conditions = Q(owner_id=user.userId) | Q(shared_with__contains=[str(user.userId)])
                if user.team_id:
                    conditions = conditions | Q(team_id=user.team_id, visibility="team")
                conditions = conditions | Q(visibility="company")
                leads_qs = leads_qs.filter(conditions).distinct()
                
                # Opportunities
                opps_qs = Opportunity.objects.filter(company_id=company_id)
                conditions = Q(owner_id=user.userId) | Q(shared_with__contains=[str(user.userId)])
                if user.team_id:
                    conditions = conditions | Q(team_id=user.team_id, visibility="team")
                conditions = conditions | Q(visibility="company")
                opps_qs = opps_qs.filter(conditions).distinct()
                
                sales_data = {
                    "leads": {
                        "total": leads_qs.count(),
                        "by_status": dict(leads_qs.values("status").annotate(count=Count("lead_id")).values_list("status", "count")),
                    },
                    "opportunities": {
                        "total": opps_qs.count(),
                        "by_stage": dict(opps_qs.values("stage").annotate(count=Count("opp_id")).values_list("stage", "count")),
                        "total_value": float(opps_qs.aggregate(total=Sum("amount"))["total"] or 0),
                    },
                }
            except Exception as e:
                logger.warning(f"Error fetching sales data: {e}")
                sales_data = {"leads": {"total": 0, "by_status": {}}, "opportunities": {"total": 0, "by_stage": {}, "total_value": 0}}

            # Recent activity (last 7 days)
            recent_activity = []
            try:
                from app.workspace.sales.models import Activity
                activities = Activity.objects.filter(
                    company_id=company_id,
                    occurred_at__gte=timezone.now() - timedelta(days=7)
                ).select_related("actor")[:10]
                
                recent_activity = [
                    {
                        "id": str(act.activity_id),
                        "type": act.entity_type,
                        "kind": act.kind,
                        "actor": act.actor.email if act.actor else None,
                        "occurred_at": act.occurred_at.isoformat(),
                    }
                    for act in activities
                ]
            except Exception as e:
                logger.warning(f"Error fetching recent activity: {e}")

            summary = {
                "projects": projects_data,
                "tasks": tasks_data,
                "sales": sales_data,
                "recent_activity": recent_activity,
            }

            return api_response(200, "success", summary)

        except Exception as exc:
            return self._handle_exception(exc, "DashboardViewSet.summary")

    @extend_schema(tags=["Dashboard"], summary="Get quick actions")
    @action(detail=False, methods=["get"])
    def quick_actions(self, request):
        """
        Get suggested quick actions based on user context
        """
        try:
            user = request.user
            actions = []

            # Check if user has incomplete onboarding
            try:
                from app.platform.onboarding.views import get_onboarding_status
                onboarding_status = get_onboarding_status(request)
                if onboarding_status and onboarding_status.get("progress", 100) < 100:
                    actions.append({
                        "id": "complete_onboarding",
                        "label": "Complete Setup",
                        "url": "/onboarding/setup",
                        "priority": "high",
                    })
            except:
                pass

            # Check for overdue tasks
            try:
                from app.workspace.tasks.models import Task
                overdue_count = Task.objects.filter(
                    company_id=user.company_id,
                    assignee_id=user.userId,
                    due_date__lt=timezone.now()
                ).exclude(status__in=["completed", "done", "cancelled"]).count()
                
                if overdue_count > 0:
                    actions.append({
                        "id": "review_overdue_tasks",
                        "label": f"Review {overdue_count} Overdue Task{'s' if overdue_count > 1 else ''}",
                        "url": "/workspace/tasks?overdue=true",
                        "priority": "high",
                    })
            except:
                pass

            # Check for pending tasks assigned to me
            try:
                from app.workspace.tasks.models import Task
                pending_count = Task.objects.filter(
                    company_id=user.company_id,
                    assignee_id=user.userId,
                    status__in=["todo", "in_progress"]
                ).count()
                
                if pending_count > 0:
                    actions.append({
                        "id": "view_my_tasks",
                        "label": f"View {pending_count} Pending Task{'s' if pending_count > 1 else ''}",
                        "url": "/workspace/tasks?assignee_id=" + str(user.userId),
                        "priority": "medium",
                    })
            except:
                pass

            return api_response(200, "success", {"actions": actions})

        except Exception as exc:
            return self._handle_exception(exc, "DashboardViewSet.quick_actions")

