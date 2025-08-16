from datetime import datetime
from django.db.models import Count
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, SAFE_METHODS, IsAuthenticated

from report.models import FarmerIssue, FarmerIssueReply
from users.serializer.issues import FarmerIssueSerializer, FarmerIssueReplySerializer


class IsOwnerOrReadOnly(BasePermission):
    """
    Only owners (farmers) can edit or delete their own issues.
    Others can read only.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.farmer == request.user


class IsAdminOrReadOnly(BasePermission):
    """
    Admin levels can reply to issues, others are read-only.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        admin_levels = [
            "super_admin",
            "district_officer",
            "sector_officer",
            "cell_officer",
        ]
        return user.user_level in admin_levels


class FarmerIssueViewSet(viewsets.ModelViewSet):
    serializer_class = FarmerIssueSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = FarmerIssue.objects.all()

        # Filters
        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")
        day = self.request.query_params.get("day")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        status = self.request.query_params.get("status")  # pending, resolved, approved

        if year:
            queryset = queryset.filter(reported_at__year=year)
        if month:
            queryset = queryset.filter(reported_at__month=month)
        if day:
            queryset = queryset.filter(reported_at__day=day)
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")
                queryset = queryset.filter(reported_at__range=[start, end])
            except ValueError:
                pass  # Ignore invalid date format

        if status and status.lower() in ["pending", "resolved", "approved"]:
            queryset = queryset.filter(status__iexact=status)

        return queryset

    def get_permissions(self):
        if self.action == "reply":
            permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
        elif self.action in ["update", "partial_update", "destroy"]:
            permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def list(self, request, *args, **kwargs):
        group_by = request.query_params.get("group_by")  # day, month, year
        queryset = self.get_queryset()

        if group_by == "day":
            queryset = (
                queryset.annotate(period=TruncDay("reported_at"))
                .values("period", "issue_type")
                .annotate(total=Count("id"))
                .order_by("period", "issue_type")
            )
        elif group_by == "month":
            queryset = (
                queryset.annotate(period=TruncMonth("reported_at"))
                .values("period", "issue_type")
                .annotate(total=Count("id"))
                .order_by("period", "issue_type")
            )
        elif group_by == "year":
            queryset = (
                queryset.annotate(period=TruncYear("reported_at"))
                .values("period", "issue_type")
                .annotate(total=Count("id"))
                .order_by("period", "issue_type")
            )

            return Response(queryset)

        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(farmer=self.request.user)

    @action(detail=True, methods=["post"])
    def reply(self, request, pk=None):
        issue = self.get_object()
        serializer = FarmerIssueReplySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(issue=issue, responder=request.user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
