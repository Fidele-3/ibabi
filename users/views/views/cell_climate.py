from rest_framework import viewsets, status
from rest_framework.response import Response
from django.utils import timezone
from report.models import CellClimateData, Cell
from users.serializer.climate_data import CellClimateDataSerializer
from users.utils.cell_data import fetch_live_data  # your live API call function
from users.models import UserProfile 

class CellClimateDataViewSet(viewsets.ViewSet):
    """
    ViewSet to retrieve climate data for a cell.
    Open to everyone (no authentication required).
    """
    permission_classes = []

    def get_cell_by_location(self, lat, lon, precision=5):
        """
        Try to match a cell approximately by latitude and longitude.
        Precision: number of decimal points to match.
        """
        factor = 10 ** precision
        return Cell.objects.filter(
            latitude__gte=(lat - 1/factor),
            latitude__lte=(lat + 1/factor),
            longitude__gte=(lon - 1/factor),
            longitude__lte=(lon + 1/factor)
        ).first()

     # make sure this points to your actual profile model

    def get_cell(self, request):
        """
        Determine which cell to use based on:
        1. Lat/Lon from frontend
        2. Authenticated user's profile
        3. Explicit cell_id query param
        """
        # 1. Lat/Lon from query
        lat = request.query_params.get("lat")
        lon = request.query_params.get("lon")
        if lat and lon:
            try:
                lat = float(lat)
                lon = float(lon)
            except ValueError:
                return None
            # Try precision 5 → 4 → 3
            for precision in [5, 4, 3]:
                cell = self.get_cell_by_location(lat, lon, precision)
                if cell:
                    return cell

        # 2. Authenticated user fallback
        if request.user.is_authenticated:
            try:
                profile = UserProfile.objects.get(user=request.user)
                if profile.cell:
                    return profile.cell
            except UserProfile.DoesNotExist:
                pass  # No profile, continue

        # 3. cell_id fallback
        cell_id = request.query_params.get("cell_id")
        if cell_id:
            try:
                return Cell.objects.get(id=cell_id)
            except Cell.DoesNotExist:
                return None

        return None


    def retrieve(self, request, pk=None):
        """
        Handles GET /cell-climate/ endpoint.
        """
        # Determine the cell
        cell = self.get_cell(request)
        if not cell:
            return Response({"detail": "Cell not found"}, status=status.HTTP_404_NOT_FOUND)

        # Retrieve stored data
        data_obj = CellClimateData.objects.filter(cell=cell).first()
        if data_obj:
            serializer = CellClimateDataSerializer(data_obj)
            return Response(serializer.data)

        # Fallback to live API
        lat = request.query_params.get("lat")
        lon = request.query_params.get("lon")
        live_data = fetch_live_data(cell, lat=lat, lon=lon)
        if live_data:
            return Response(live_data)

        return Response({"detail": "Data not found"}, status=status.HTTP_404_NOT_FOUND)
