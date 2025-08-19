from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from report.models import (
    Land, LivestockLocation, HarvestReport, LivestockProduction,
    ResourceRequest
)
from report.models.issues import FarmerIssue
from users.serializer.issues import FarmerIssueSerializer
from users.serializer.resources import ResourceRequestSerializer
from users.serializer.land import LandSerializer, LivestockLocationSerializer
from users.serializer.products import HarvestReportSerializer, LivestockProductionSerializer
from datetime import datetime

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 100  # default page size
    page_size_query_param = 'page_size'
    max_page_size = 500  # safety cap

class AIDataViewSet(viewsets.ViewSet):
    """
    Open AI endpoint exposing lands, livestock locations,
    reports, issues, and resource requests in paginated JSON objects.
    Supports ?all=true to return full datasets.
    """
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination

    def paginate_queryset(self, queryset, request):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        return page, paginator

    def filter_by_date(self, queryset, request):
        """Filter queryset by optional date parameters"""
        year = request.query_params.get("year")
        month = request.query_params.get("month")
        day = request.query_params.get("day")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

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
                pass
        return queryset

    def serialize_paginated(self, queryset, serializer_class, request):
        """Paginate OR return all results based on ?all=true"""
        queryset = queryset.order_by("id")  # ensures consistent pagination

        if request.query_params.get("all", "").lower() == "true":
            serialized_data = serializer_class(
                queryset.iterator(chunk_size=500), many=True
            ).data
            return {
                "count": queryset.count(),
                "next": None,
                "previous": None,
                "results": serialized_data,
            }

        # Default = paginated
        page, paginator = self.paginate_queryset(queryset, request)
        serialized_data = serializer_class(page, many=True).data
        return {
            "count": paginator.page.paginator.count if paginator.page else len(serialized_data),
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": serialized_data,
        }

    def list(self, request, *args, **kwargs):
        """Return all datasets in a structured, paginated or full format"""

        lands = Land.objects.all()
        lands_data = self.serialize_paginated(lands, LandSerializer, request)

        livestock_locations = LivestockLocation.objects.all()
        livestock_data = self.serialize_paginated(livestock_locations, LivestockLocationSerializer, request)

        harvest_reports = self.filter_by_date(HarvestReport.objects.all(), request)
        harvest_data = self.serialize_paginated(harvest_reports, HarvestReportSerializer, request)

        livestock_reports = self.filter_by_date(LivestockProduction.objects.all(), request)
        livestock_report_data = self.serialize_paginated(livestock_reports, LivestockProductionSerializer, request)

        issues = FarmerIssue.objects.all()
        issues_data = self.serialize_paginated(issues, FarmerIssueSerializer, request)

        resource_requests = ResourceRequest.objects.all()
        resource_data = self.serialize_paginated(resource_requests, ResourceRequestSerializer, request)

        response = {
            "lands_and_livestock_locations": {
                "lands": lands_data,
                "livestock_locations": livestock_data
            },
            "reports": {
                "harvest_reports": harvest_data,
                "livestock_production_reports": livestock_report_data
            },
            "issues": issues_data,
            "resource_requests": resource_data
        }

        return Response(response)
