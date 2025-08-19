from rest_framework import serializers
from users.models.addresses import Province, District, Sector, Cell, Village
from report.models import FarmerIssue, FarmerIssueReply

ALLOWED_STATUS = ['RESOLVED', 'APPROVED', 'PENDING']

class FarmerIssueReplySerializer(serializers.ModelSerializer):
    responder_name = serializers.CharField(source="responder.full_names", read_only=True)
    status = serializers.CharField(required=False)  # optional status passed in reply

    class Meta:
        model = FarmerIssueReply
        fields = ['id', 'issue', 'responder', 'responder_name', 'message', 'replied_at', 'status']
        read_only_fields = ['id', 'issue', 'responder', 'responder_name', 'replied_at']

    def create(self, validated_data):
        status = validated_data.pop('status', None)
        reply = super().create(validated_data)

        # Update the related FarmerIssue status if status is provided
        if status is not None:
            reply.issue.status = status  # keep the original casing
            reply.issue.save()

        return reply

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
    status = serializers.SerializerMethodField()  # convert status to lowercase

    # Nested replies
    replies = serializers.SerializerMethodField()

    class Meta:
        model = FarmerIssue
        fields = [
            'id', 'farmer', 'farmer_name', 'issue_type', 'description', 'photo',
            'latitude', 'longitude', 'reported_at',
            'province', 'district', 'sector', 'cell', 'village',
            'status', 'replies'
        ]
        read_only_fields = ['id', 'reported_at', 'farmer_name', 'replies']

    def get_status(self, obj):
        return obj.status.lower() if obj.status else None

    def get_replies(self, obj):
        request = self.context.get('request', None)
        issue_id = request.query_params.get('issue_id') if request else None

        if issue_id:
            replies_qs = obj.replies.filter(issue_id=issue_id)
        else:
            replies_qs = obj.replies.all()

        return FarmerIssueReplySerializer(replies_qs, many=True).data

    def validate(self, data):
        province = data.get('province')
        district = data.get('district')
        sector = data.get('sector')
        cell = data.get('cell')
        village = data.get('village')

        if district.province_id != province.id:
            raise serializers.ValidationError("District does not belong to the selected Province.")
        if sector.district_id != district.id:
            raise serializers.ValidationError("Sector does not belong to the selected District.")
        if cell.sector_id != sector.id:
            raise serializers.ValidationError("Cell does not belong to the selected Sector.")
        if village.cell_id != cell.id:
            raise serializers.ValidationError("Village does not belong to the selected Cell.")

        return data

    def get_latitude(self, obj):
        return obj.latitude if obj.latitude is not None else getattr(obj.cell, 'latitude', None)

    def get_longitude(self, obj):
        return obj.longitude if obj.longitude is not None else getattr(obj.cell, 'longitude', None)
