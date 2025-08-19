from rest_framework import serializers
from report.models import FarmerInventory

class FarmerInventorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    quantity_remaining = serializers.SerializerMethodField()

    class Meta:
        model = FarmerInventory
        fields = [
            'id',
            'farmer',
            'product',
            'product_name',
            'quantity_added',
            'quantity_allocated',
            'quantity_deducted',
            'quantity_remaining',
            'updated_at',
        ]
        read_only_fields = ['farmer', 'quantity_remaining', 'updated_at']

    def get_quantity_remaining(self, obj):
        return obj.quantity_remaining

    def validate(self, data):
        # Deduction logic handled in the view
        return data
