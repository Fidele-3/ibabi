from rest_framework.permissions import BasePermission, SAFE_METHODS
from users.models import Product, ProductPrice, RecommendedQuantity
from report.models import HarvestReport, LivestockProduction


class RoleBasedPermission(BasePermission):
    """
    Controls object-level permissions based on role and ownership.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        if request.method in SAFE_METHODS:
            return True

        return True  

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        # Products and related data → only super admins can modify
        if isinstance(obj, (Product, ProductPrice, RecommendedQuantity)):
            return getattr(request.user, "is_super_admin", False)

        # Reports → only the farmer who created them can modify
        if isinstance(obj, (HarvestReport, LivestockProduction)):
            return obj.farmer == request.user

        return False


# views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from users.utils.filters import filter_by_role_and_location
from users.models import Product, ProductPrice, RecommendedQuantity
from report.models import HarvestReport, LivestockProduction
from users.serializer.products import (
    ProductSerializer,
    ProductPriceSerializer,
    RecommendedQuantitySerializer,
    HarvestReportSerializer,
    LivestockProductionSerializer
)

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    def get_queryset(self):
        queryset = Product.objects.all()
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category__iexact=category)  # case-insensitive match
        return queryset
    

class ProductPriceViewSet(viewsets.ModelViewSet):
    queryset = ProductPrice.objects.all()
    serializer_class = ProductPriceSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]

class RecommendedQuantityViewSet(viewsets.ModelViewSet):
    queryset = RecommendedQuantity.objects.all()
    serializer_class = RecommendedQuantitySerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]

from datetime import datetime
from django.db.models import Sum, Count
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class HarvestReportViewSet(viewsets.ModelViewSet):
    serializer_class = HarvestReportSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]

    def get_queryset(self):
        queryset = filter_by_role_and_location(
            HarvestReport.objects.all(),
            self.request.user
        )

        # Filters
        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")
        day = self.request.query_params.get("day")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if year:
            queryset = queryset.filter(report_date__year=year)
        if month:
            queryset = queryset.filter(report_date__month=month)
        if day:
            queryset = queryset.filter(report_date__day=day)
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")
                queryset = queryset.filter(report_date__range=[start, end])
            except ValueError:
                pass  # Ignore invalid date format

        return queryset

    def list(self, request, *args, **kwargs):
        group_by = request.query_params.get("group_by")  # day, month, year
        queryset = self.get_queryset()

        if group_by:
            if group_by == "day":
                queryset = (
                    queryset.annotate(period=TruncDay("report_date"))
                    .values("period")
                    .annotate(total_quantity=Sum("quantity"), count=Count("id"))
                    .order_by("period")
                )
            elif group_by == "month":
                queryset = (
                    queryset.annotate(period=TruncMonth("report_date"))
                    .values("period")
                    .annotate(total_quantity=Sum("quantity"), count=Count("id"))
                    .order_by("period")
                )
            elif group_by == "year":
                queryset = (
                    queryset.annotate(period=TruncYear("report_date"))
                    .values("period")
                    .annotate(total_quantity=Sum("quantity"), count=Count("id"))
                    .order_by("period")
                )
            return Response(queryset)

        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(farmer=self.request.user)


class LivestockProductionViewSet(viewsets.ModelViewSet):
    serializer_class = LivestockProductionSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]

    def get_queryset(self):
        queryset = filter_by_role_and_location(
            LivestockProduction.objects.all(),
            self.request.user
        )

        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")
        day = self.request.query_params.get("day")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if year:
            queryset = queryset.filter(report_date__year=year)
        if month:
            queryset = queryset.filter(report_date__month=month)
        if day:
            queryset = queryset.filter(report_date__day=day)
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")
                queryset = queryset.filter(report_date__date__range=[start, end])
            except ValueError:
                pass

        return queryset

    def list(self, request, *args, **kwargs):
        group_by = request.query_params.get("group_by")
        queryset = self.get_queryset()

        if group_by:
            if group_by == "day":
                queryset = (
                    queryset.annotate(period=TruncDay("report_date"))
                    .values("period")
                    .annotate(total_quantity=Sum("quantity"), count=Count("id"))
                    .order_by("period")
                )
            elif group_by == "month":
                queryset = (
                    queryset.annotate(period=TruncMonth("report_date"))
                    .values("period")
                    .annotate(total_quantity=Sum("quantity"), count=Count("id"))
                    .order_by("period")
                )
            elif group_by == "year":
                queryset = (
                    queryset.annotate(period=TruncYear("report_date"))
                    .values("period")
                    .annotate(total_quantity=Sum("quantity"), count=Count("id"))
                    .order_by("period")
                )
            return Response(queryset)

        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(farmer=self.request.user)
