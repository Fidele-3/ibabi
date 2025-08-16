from rest_framework import serializers
from report.models import DistrictInventory, CellInventory


class DistrictInventorySerializer(serializers.ModelSerializer):
    district = serializers.PrimaryKeyRelatedField(read_only=True)
    quantity_remaining = serializers.SerializerMethodField()
    officer_name = serializers.CharField(source="district.district_officer.full_names", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_category = serializers.CharField(source='product.category', read_only=True)
    class Meta:
        model = DistrictInventory
        fields = ['id', 'district', 'product', 'quantity_added', 'quantity_at_cell', 'quantity_remaining', 'officer_name', 'district_name', 'product_name', 'product_category']

    def get_quantity_remaining(self, obj):
        # Compute remaining = quantity_added - quantity_at_cell
        return float(obj.quantity_added) - float(obj.quantity_at_cell)

class CellInventorySerializer(serializers.ModelSerializer):
    officer_name = serializers.CharField(source="cell.cell_officer.full_names", read_only=True)
    sector_name = serializers.CharField(source='cell.sector.name', read_only=True)
    cell_name = serializers.CharField(source='cell.name', read_only=True)
    district_name = serializers.CharField(source='cell.sector.district.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_category = serializers.CharField(source='product.category', read_only=True)
    class Meta:
        model = CellInventory
        fields = ['id', 'cell', 'sector', 'district', 'sector_name', 'district_name', 'product', 'quantity_available', 'updated_at', 'officer_name', 'product_name', 'cell_name', 'product_category']
        read_only_fields = ['updated_at']
