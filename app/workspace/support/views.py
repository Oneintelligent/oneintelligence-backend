# app/workspace/support/views.py
import logging
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Case, When, IntegerField, Value
from django.core.paginator import Paginator
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Ticket, TicketComment, TicketAttachment
from .serializers import (
    TicketSerializer, TicketCommentSerializer, TicketAttachmentSerializer
)
from .permissions import can_view_ticket, can_edit_ticket, can_delete_ticket, HasSupportPermission
from app.platform.rbac.mixins import RBACPermissionMixin
from app.platform.rbac.constants import Modules, Permissions
from app.utils.response import api_response

logger = logging.getLogger(__name__)

# Pagination constants
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500


@extend_schema_view(
    list=extend_schema(exclude=False),
    retrieve=extend_schema(exclude=False),
    create=extend_schema(exclude=False),
    update=extend_schema(exclude=False),
    partial_update=extend_schema(exclude=False),
    destroy=extend_schema(exclude=False),
)
class TicketViewSet(viewsets.ViewSet, RBACPermissionMixin):
    """
    Tickets — Action-Oriented Interface (AOI) ViewSet
    Enterprise-grade RBAC integration
    """
    permission_classes = [IsAuthenticated]
    module = Modules.SUPPORT

    def _handle_exception(self, exc: Exception, where: str = ""):
        logger.exception("%s: %s", where, str(exc))
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            status="failure",
            data={},
            error_code="SERVER_ERROR",
            error_message=str(exc),
        )

    @extend_schema(tags=["Support"], summary="List tickets (scoped to user)")
    def list(self, request):
        try:
            user = request.user
            # Optimize query: use select_related for ForeignKeys
            # Don't prefetch comments/attachments in list view (expensive, fetch on demand)
            qs = Ticket.objects.filter(company_id=user.company_id).select_related(
                "owner", "assignee", "account", "project", "task", "team", "created_by", "company"
            )

            # Filter by visibility and assignment
            conditions = Q(owner_id=user.userId) | Q(assignee_id=user.userId) | Q(created_by_id=user.userId)
            conditions = conditions | Q(visibility="company")
            if user.team_id:
                conditions = conditions | Q(team_id=user.team_id, visibility="team")
            conditions = conditions | Q(visibility="shared", shared_with__contains=[str(user.userId)])
            
            qs = qs.filter(conditions).distinct()

            # Search
            qtext = request.query_params.get("q")
            if qtext:
                qs = qs.filter(
                    Q(subject__icontains=qtext) | 
                    Q(description__icontains=qtext) |
                    Q(customer_email__icontains=qtext) |
                    Q(customer_name__icontains=qtext)
                )

            # Filter by status
            status_filter = request.query_params.get("status")
            if status_filter:
                qs = qs.filter(status=status_filter)

            # Filter by priority
            priority_filter = request.query_params.get("priority")
            if priority_filter:
                qs = qs.filter(priority=priority_filter)

            # Filter by type
            type_filter = request.query_params.get("type")
            if type_filter:
                qs = qs.filter(type=type_filter)

            # Filter by source
            source_filter = request.query_params.get("source")
            if source_filter:
                qs = qs.filter(source=source_filter)

            # Filter by account
            account_id = request.query_params.get("account_id")
            if account_id:
                qs = qs.filter(account_id=account_id)

            # Filter by project
            project_id = request.query_params.get("project_id")
            if project_id:
                qs = qs.filter(project_id=project_id)

            # Filter by task
            task_id = request.query_params.get("task_id")
            if task_id:
                qs = qs.filter(task_id=task_id)

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
                qs = qs.filter(due_date__lt=timezone.now()).exclude(status__in=["resolved", "closed"])

            # Filter my tickets
            my_tickets = request.query_params.get("my_tickets")
            if my_tickets == "true":
                qs = qs.filter(Q(assignee_id=user.userId) | Q(owner_id=user.userId))

            # Order by
            order_by = request.query_params.get("order_by", "-updated_at")
            qs = qs.order_by(order_by)

            # Pagination for scalability
            page = int(request.query_params.get("page", 1))
            page_size = min(int(request.query_params.get("page_size", DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
            
            paginator = Paginator(qs, page_size)
            total_count = paginator.count
            total_pages = paginator.num_pages
            
            try:
                page_obj = paginator.page(page)
                tickets = page_obj.object_list
            except Exception:
                # Invalid page number, return first page
                page_obj = paginator.page(1)
                tickets = page_obj.object_list
                page = 1

            serializer = TicketSerializer(tickets, many=True, context={"request": request})
            return api_response(200, "success", {
                "results": serializer.data,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": page_obj.has_next(),
                    "has_previous": page_obj.has_previous(),
                }
            })

        except Exception as exc:
            return self._handle_exception(exc, "TicketViewSet.list")

    @extend_schema(tags=["Support"], summary="Retrieve a ticket")
    def retrieve(self, request, pk=None):
        try:
            ticket = get_object_or_404(
                Ticket.objects.select_related(
                    "owner", "assignee", "account", "project", "task", "team", "created_by"
                ).prefetch_related("comments__author", "attachments"),
                ticket_id=pk
            )
            if not can_view_ticket(request.user, ticket):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have access to this ticket")
            
            serializer = TicketSerializer(ticket, context={"request": request})
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "TicketViewSet.retrieve")

    @extend_schema(tags=["Support"], summary="Create a ticket", request=TicketSerializer)
    @transaction.atomic
    def create(self, request):
        try:
            serializer = TicketSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            
            # Ensure ticket is linked to user's company and the creating user
            # Default owner to the creating user if not specified
            owner = None
            if request.data.get("owner_id"):
                from app.platform.accounts.models import User
                try:
                    owner = User.objects.get(userId=request.data.get("owner_id"), company_id=request.user.company_id)
                except User.DoesNotExist:
                    pass  # Will default to request.user below
            
            # If no owner_id provided or owner lookup failed, default to request.user
            if not owner:
                owner = request.user
            
            ticket = serializer.save(
                company_id=request.user.company_id,  # Always link to user's company
                created_by=request.user,  # Always set creator
                owner=owner  # Default to request.user if not specified
            )
            return api_response(201, "success", TicketSerializer(ticket, context={"request": request}).data)
        except Exception as exc:
            return self._handle_exception(exc, "TicketViewSet.create")

    @extend_schema(tags=["Support"], summary="Update a ticket", request=TicketSerializer)
    @transaction.atomic
    def update(self, request, pk=None):
        try:
            # Optimize query with select_related for related objects
            ticket = get_object_or_404(
                Ticket.objects.select_related("owner", "assignee", "account", "project", "task", "team", "created_by"),
                ticket_id=pk
            )
            if not can_edit_ticket(request.user, ticket):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have permission to edit this ticket")
            
            serializer = TicketSerializer(ticket, data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "TicketViewSet.update")

    @extend_schema(tags=["Support"], summary="Partially update a ticket", request=TicketSerializer)
    @transaction.atomic
    def partial_update(self, request, pk=None):
        try:
            # Optimize query with select_related for related objects
            ticket = get_object_or_404(
                Ticket.objects.select_related("owner", "assignee", "account", "project", "task", "team", "created_by"),
                ticket_id=pk
            )
            if not can_edit_ticket(request.user, ticket):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have permission to edit this ticket")
            
            serializer = TicketSerializer(ticket, data=request.data, partial=True, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "TicketViewSet.partial_update")

    @extend_schema(tags=["Support"], summary="Delete a ticket")
    @transaction.atomic
    def destroy(self, request, pk=None):
        try:
            # Optimize query - only need company_id for permission check
            ticket = get_object_or_404(
                Ticket.objects.only("ticket_id", "company_id", "owner_id", "created_by_id"),
                ticket_id=pk
            )
            if not can_delete_ticket(request.user, ticket):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have permission to delete this ticket")
            
            ticket.delete()
            return api_response(200, "success", {"ticket_id": str(pk)})
        except Exception as exc:
            return self._handle_exception(exc, "TicketViewSet.destroy")

    @extend_schema(tags=["Support"], summary="Add comment to ticket", request=TicketCommentSerializer)
    @action(detail=True, methods=["post"])
    @transaction.atomic
    def add_comment(self, request, pk=None):
        try:
            ticket = get_object_or_404(Ticket, ticket_id=pk)
            if not can_view_ticket(request.user, ticket):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have access to this ticket")
            
            serializer = TicketCommentSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            comment = serializer.save(
                ticket=ticket,
                author=request.user
            )
            return api_response(201, "success", TicketCommentSerializer(comment, context={"request": request}).data)
        except Exception as exc:
            return self._handle_exception(exc, "TicketViewSet.add_comment")

    @extend_schema(tags=["Support"], summary="Get ticket statistics")
    @action(detail=False, methods=["get"])
    def stats(self, request):
        try:
            user = request.user
            qs = Ticket.objects.filter(company_id=user.company_id)
            
            # Apply same visibility filters as list
            conditions = Q(owner_id=user.userId) | Q(assignee_id=user.userId) | Q(created_by_id=user.userId)
            conditions = conditions | Q(visibility="company")
            if user.team_id:
                conditions = conditions | Q(team_id=user.team_id, visibility="team")
            conditions = conditions | Q(visibility="shared", shared_with__contains=[str(user.userId)])
            qs = qs.filter(conditions).distinct()
            
            # Optimize stats calculation with single aggregated query instead of multiple count queries
            now = timezone.now()
            stats = qs.aggregate(
                total=Count("ticket_id"),
                new=Count("ticket_id", filter=Q(status="new")),
                open=Count("ticket_id", filter=Q(status="open")),
                pending=Count("ticket_id", filter=Q(status="pending")),
                resolved=Count("ticket_id", filter=Q(status="resolved")),
                closed=Count("ticket_id", filter=Q(status="closed")),
                urgent=Count("ticket_id", filter=Q(priority="urgent") & ~Q(status__in=["resolved", "closed"])),
                overdue=Count("ticket_id", filter=Q(due_date__lt=now) & ~Q(status__in=["resolved", "closed"])),
                my_tickets=Count("ticket_id", filter=Q(assignee_id=user.userId) | Q(owner_id=user.userId)),
            )
            
            return api_response(200, "success", stats)
        except Exception as exc:
            return self._handle_exception(exc, "TicketViewSet.stats")


@extend_schema_view(
    list=extend_schema(exclude=False),
    retrieve=extend_schema(exclude=False),
    create=extend_schema(exclude=False),
    update=extend_schema(exclude=False),
    partial_update=extend_schema(exclude=False),
    destroy=extend_schema(exclude=False),
)
class TicketCommentViewSet(viewsets.ViewSet):
    """
    Ticket Comments — Action-Oriented Interface (AOI) ViewSet
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

    @extend_schema(tags=["Support"], summary="List comments for a ticket")
    def list(self, request):
        try:
            ticket_id = request.query_params.get("ticket_id")
            if not ticket_id:
                return api_response(400, "failure", {}, "BAD_REQUEST", "ticket_id is required")
            
            ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
            if not can_view_ticket(request.user, ticket):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have access to this ticket")
            
            comments = ticket.comments.all().select_related("author").order_by("-created_at")
            
            # Pagination for comments
            page = int(request.query_params.get("page", 1))
            page_size = min(int(request.query_params.get("page_size", 50)), MAX_PAGE_SIZE)
            
            paginator = Paginator(comments, page_size)
            total_count = paginator.count
            total_pages = paginator.num_pages
            
            try:
                page_obj = paginator.page(page)
                comments_list = page_obj.object_list
            except Exception:
                page_obj = paginator.page(1)
                comments_list = page_obj.object_list
                page = 1
            
            serializer = TicketCommentSerializer(comments_list, many=True, context={"request": request})
            return api_response(200, "success", {
                "results": serializer.data,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": page_obj.has_next(),
                    "has_previous": page_obj.has_previous(),
                }
            })
        except Exception as exc:
            return self._handle_exception(exc, "TicketCommentViewSet.list")

    @extend_schema(tags=["Support"], summary="Create a comment")
    @transaction.atomic
    def create(self, request):
        try:
            ticket_id = request.data.get("ticket_id") or request.data.get("ticket")
            if not ticket_id:
                return api_response(400, "failure", {}, "BAD_REQUEST", "ticket_id is required")
            
            ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
            if not can_view_ticket(request.user, ticket):
                return api_response(403, "failure", {}, "FORBIDDEN", "You don't have access to this ticket")
            
            serializer = TicketCommentSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            comment = serializer.save(
                ticket=ticket,
                author=request.user
            )
            return api_response(201, "success", TicketCommentSerializer(comment, context={"request": request}).data)
        except Exception as exc:
            return self._handle_exception(exc, "TicketCommentViewSet.create")

    @extend_schema(tags=["Support"], summary="Update a comment")
    @transaction.atomic
    def update(self, request, pk=None):
        try:
            comment = get_object_or_404(TicketComment, comment_id=pk)
            if comment.author_id != request.user.userId:
                return api_response(403, "failure", {}, "FORBIDDEN", "You can only edit your own comments")
            
            serializer = TicketCommentSerializer(comment, data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return api_response(200, "success", serializer.data)
        except Exception as exc:
            return self._handle_exception(exc, "TicketCommentViewSet.update")

    @extend_schema(tags=["Support"], summary="Delete a comment")
    @transaction.atomic
    def destroy(self, request, pk=None):
        try:
            comment = get_object_or_404(TicketComment, comment_id=pk)
            if comment.author_id != request.user.userId:
                return api_response(403, "failure", {}, "FORBIDDEN", "You can only delete your own comments")
            
            comment.delete()
            return api_response(200, "success", {"comment_id": str(pk)})
        except Exception as exc:
            return self._handle_exception(exc, "TicketCommentViewSet.destroy")

