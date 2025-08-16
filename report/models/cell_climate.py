from django.db import models
from users.models.customuser import CustomUser
from users.models.addresses import Province, District, Sector, Cell, Village
import uuid


class CellClimateData(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cell = models.OneToOneField(Cell, on_delete=models.CASCADE, related_name="climate_data")
    next_24h_forecast = models.JSONField(null=True, blank=True)    # e.g., predicted next 24 hours
    past_3_months_data = models.JSONField(null=True, blank=True)
      # e.g., past 3 months data
    fetched_at = models.DateTimeField(auto_now=True)
    historical_fetched_at = models.DateTimeField(null=True, blank=True)
    forecast_fetched_at = models.DateTimeField(null=True, blank=True)