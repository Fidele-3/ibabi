from rest_framework import viewsets, permissions
from rest_framework.response import Response
from report.models import (
    Land, LivestockLocation, HarvestReport, LivestockProduction,
     ResourceRequest
)
from report.models.issues import FarmerIssue
from users.serializer.issues import FarmerIssueSerializer
from users.serializer.resources import ResourceRequestSerializer
from users.serializer.land import LandSerializer, LivestockLocationSerializer
from users.serializer.products import HarvestReportSerializer, LivestockProductionSerializer


from users.serializer.resources import ResourceRequestSerializer

from datetime import datetime

class AIDataViewSet(viewsets.ViewSet):
    """
    Fully open AI endpoint exposing lands, livestock locations,
    reports, issues, and resource requests in four JSON objects.
    """
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        # 1️⃣ Lands and Livestock Locations
        lands = Land.objects.all()
        livestock_locations = LivestockLocation.objects.all()
        lands_data = LandSerializer(lands, many=True).data
        livestock_data = LivestockLocationSerializer(livestock_locations, many=True).data

        # 2️⃣ Reports: HarvestReport + LivestockProduction
        harvest_reports = HarvestReport.objects.all()
        livestock_reports = LivestockProduction.objects.all()

        # Optional date filtering
        year = request.query_params.get("year")
        month = request.query_params.get("month")
        day = request.query_params.get("day")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        def filter_by_date(queryset):
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

        harvest_reports = filter_by_date(harvest_reports)
        livestock_reports = filter_by_date(livestock_reports)

        harvest_data = HarvestReportSerializer(harvest_reports, many=True).data
        livestock_report_data = LivestockProductionSerializer(livestock_reports, many=True).data

        # 3️⃣ Issues
        issues = FarmerIssue.objects.all()
        issues_data = FarmerIssueSerializer(issues, many=True).data

        # 4️⃣ Resource Requests
        resource_requests = ResourceRequest.objects.all()
        resource_requests_data = ResourceRequestSerializer(resource_requests, many=True).data

        return Response({
            "lands_and_livestock_locations": {
                "lands": lands_data,
                "livestock_locations": livestock_data
            },
            "reports": {
                "harvest_reports": harvest_data,
                "livestock_production_reports": livestock_report_data
            },
            "issues": issues_data,
            "resource_requests": resource_requests_data
        })
