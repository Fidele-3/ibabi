import logging
from datetime import datetime
from django.db.models import Count
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, SAFE_METHODS, IsAuthenticated

from report.models import FarmerIssue, FarmerIssueReply
from users.serializer.issues import FarmerIssueSerializer, FarmerIssueReplySerializer

logger = logging.getLogger(__name__)


class IsOwnerOrReadOnly(BasePermission):
    """Only owners (farmers) can edit or delete their own issues."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        allowed = obj.farmer == request.user
        logger.debug(
            "[PERMISSION] IsOwnerOrReadOnly user=%s method=%s allowed=%s",
            request.user,
            request.method,
            allowed,
        )
        return allowed


class IsAdminOrReadOnly(BasePermission):
    """Admin levels can reply to issues, others are read-only."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            logger.warning("[PERMISSION] Unauthorized access attempt")
            return False

        admin_levels = [
            "super_admin",
            "district_officer",
            "sector_officer",
            "cell_officer",
        ]
        allowed = str(user.user_level).lower() in [lvl.lower() for lvl in admin_levels]
        logger.debug(
            "[PERMISSION] IsAdminOrReadOnly user=%s level=%s allowed=%s",
            user,
            getattr(user, "user_level", None),
            allowed,
        )
        return allowed


class FarmerIssueViewSet(viewsets.ModelViewSet):
    serializer_class = FarmerIssueSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = FarmerIssue.objects.all()
        params = self.request.query_params.dict()
        logger.debug("[QUERYSET] Initial issues count=%s params=%s", queryset.count(), params)

        issue_id = params.get("issue_id")
        if issue_id:
            queryset = queryset.filter(id=issue_id)
            logger.debug("[QUERYSET] Filtered by issue_id=%s count=%s", issue_id, queryset.count())

        year, month, day = params.get("year"), params.get("month"), params.get("day")
        start_date, end_date, status = params.get("start_date"), params.get("end_date"), params.get("status")

        if year:
            queryset = queryset.filter(reported_at__year=year)
            logger.debug("[QUERYSET] Filtered by year=%s count=%s", year, queryset.count())
        if month:
            queryset = queryset.filter(reported_at__month=month)
            logger.debug("[QUERYSET] Filtered by month=%s count=%s", month, queryset.count())
        if day:
            queryset = queryset.filter(reported_at__day=day)
            logger.debug("[QUERYSET] Filtered by day=%s count=%s", day, queryset.count())
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")
                queryset = queryset.filter(reported_at__range=[start, end])
                logger.debug("[QUERYSET] Filtered by range %s to %s count=%s", start, end, queryset.count())
            except ValueError:
                logger.error("[QUERYSET] Invalid date format start=%s end=%s", start_date, end_date)

        if status and status.lower() in ["pending", "resolved", "approved"]:
            queryset = queryset.filter(status__iexact=status)
            logger.debug("[QUERYSET] Filtered by status=%s count=%s", status, queryset.count())

        return queryset

    def get_permissions(self):
        if self.action == "reply":
            permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
        elif self.action in ["update", "partial_update", "destroy"]:
            permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
        else:
            permission_classes = [IsAuthenticated]

        logger.debug("[PERMISSION] Action=%s Permissions=%s", self.action, permission_classes)
        return [permission() for permission in permission_classes]

    def list(self, request, *args, **kwargs):
        group_by = request.query_params.get("group_by")
        logger.debug("[LIST] user=%s group_by=%s", request.user, group_by)

        queryset = self.get_queryset()

        if group_by in ["day", "month", "year"]:
            trunc_map = {"day": TruncDay, "month": TruncMonth, "year": TruncYear}
            queryset = (
                queryset.annotate(period=trunc_map[group_by]("reported_at"))
                .values("period", "issue_type")
                .annotate(total=Count("id"))
                .order_by("period", "issue_type")
            )
            logger.debug("[LIST] Grouped by %s result count=%s", group_by, len(queryset))
            return Response(queryset)

        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        logger.debug("[RETRIEVE] user=%s kwargs=%s", request.user, kwargs)
        return super().retrieve(request, *args, **kwargs)

    def perform_create(self, serializer):
        logger.debug("[CREATE] user=%s data=%s", self.request.user, self.request.data)
        try:
            serializer.save(farmer=self.request.user)
            logger.info("[CREATE] FarmerIssue created successfully user=%s", self.request.user)
        except Exception as e:
            logger.error("[CREATE-ERROR] user=%s error=%s", self.request.user, str(e), exc_info=True)
            raise

    @action(detail=True, methods=["post"])
    def reply(self, request, pk=None):
        logger.debug("[REPLY] user=%s issue_id=%s data=%s", request.user, pk, request.data)
        issue = self.get_object()
        serializer = FarmerIssueReplySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(issue=issue, responder=request.user)
            logger.info("[REPLY] Reply added successfully issue_id=%s user=%s", pk, request.user)
            return Response(serializer.data, status=201)
        else:
            logger.warning("[REPLY-ERROR] Validation failed user=%s errors=%s", request.user, serializer.errors)
            return Response(serializer.errors, status=400)
