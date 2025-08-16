from rest_framework import serializers
from users.models.addresses import Province, District, Sector, Cell, Village
from report.models import FarmerIssue, FarmerIssueReply

class FarmerIssueReplySerializer(serializers.ModelSerializer):
    responder_name = serializers.CharField(source="responder.full_names", read_only=True)

    class Meta:
        model = FarmerIssueReply
        fields = ['id', 'issue', 'responder', 'responder_name', 'message', 'replied_at']
        read_only_fields = ['id', 'issue', 'responder', 'responder_name', 'replied_at']

class FarmerIssueSerializer(serializers.ModelSerializer):
    farmer = serializers.PrimaryKeyRelatedField(read_only=True)
    province = serializers.PrimaryKeyRelatedField(queryset=Province.objects.all())
    district = serializers.PrimaryKeyRelatedField(queryset=District.objects.all())
    sector = serializers.PrimaryKeyRelatedField(queryset=Sector.objects.all())
    cell = serializers.PrimaryKeyRelatedField(queryset=Cell.objects.all())
    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())

    farmer_name = serializers.CharField(source="farmer.full_names", read_only=True)

    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = FarmerIssue
        fields = [
            'id', 'farmer', 'farmer_name', 'issue_type', 'description', 'photo',
            'latitude', 'longitude', 'reported_at',
            'province', 'district', 'sector', 'cell', 'village',
            'status', 'replies'
        ]
        read_only_fields = ['id', 'reported_at', 'status', 'farmer_name', 'replies']

    def validate(self, data):
        province = data.get('province')
        district = data.get('district')
        sector = data.get('sector')
        cell = data.get('cell')
        village = data.get('village')

        # Province ↔ District check
        if district.province_id != province.id:
            raise serializers.ValidationError("District does not belong to the selected Province.")

        # District ↔ Sector check
        if sector.district_id != district.id:
            raise serializers.ValidationError("Sector does not belong to the selected District.")

        # Sector ↔ Cell check
        if cell.sector_id != sector.id:
            raise serializers.ValidationError("Cell does not belong to the selected Sector.")

        # Cell ↔ Village check
        if village.cell_id != cell.id:
            raise serializers.ValidationError("Village does not belong to the selected Cell.")

        return data

    def get_latitude(self, obj):
        return obj.latitude if obj.latitude is not None else getattr(obj.cell, 'latitude', None)

    def get_longitude(self, obj):
        return obj.longitude if obj.longitude is not None else getattr(obj.cell, 'longitude', None)
