from rest_framework import serializers
from report.models import CellClimateData, Cell

class CellClimateDataSerializer(serializers.ModelSerializer):
    cell_id = serializers.IntegerField(source='cell.id', read_only=True)
    cell_name = serializers.CharField(source='cell.name', read_only=True)
    latitude = serializers.FloatField(source='cell.latitude', read_only=True)
    longitude = serializers.FloatField(source='cell.longitude', read_only=True)

    class Meta:
        model = CellClimateData
        # Dynamically include all fields in the model
        fields = [
            'cell_id', 'cell_name', 'latitude', 'longitude',
            'next_24h_forecast',
            'forecast_fetched_at',
            'past_3_months_data',
            'historical_fetched_at',
        ]
        read_only_fields = fields
