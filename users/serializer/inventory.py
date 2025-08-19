from rest_framework import serializers
from report.models import DistrictInventory, CellInventory
from users.models.products import Product
class DistrictInventorySerializer(serializers.ModelSerializer):
    district = serializers.PrimaryKeyRelatedField(read_only=True)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity_added = serializers.DecimalField(max_digits=12, decimal_places=2)

    quantity_remaining = serializers.SerializerMethodField()
    officer_name = serializers.CharField(source="district.district_officer.full_names", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_category = serializers.CharField(source='product.category', read_only=True)

    class Meta:
        model = DistrictInventory
        fields = [
            'id', 'district', 'product', 'quantity_added', 'quantity_at_cell',
            'quantity_remaining', 'officer_name', 'district_name', 'product_name', 'product_category', 'quantity_remaining_at_cells', 
        ]
        read_only_fields = ['quantity_at_cell']

    def get_quantity_remaining(self, obj):
        # Use the model property for accurate remaining quantity
        return float(obj.quantity_remaining)

    def validate_quantity_added(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity added must be greater than zero.")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        district = getattr(request.user, 'managed_district', None) if request else None
        product = validated_data['product']
        quantity_to_add = validated_data['quantity_added']

        # Check if a district inventory for this product already exists
        district_inventory, created = DistrictInventory.objects.get_or_create(
            district=district,
            product=product,
            defaults={'quantity_added': 0, 'quantity_at_cell': 0, 'quantity_remaining_at_cells': 0}
        )

        # Aggregate quantities
        district_inventory.quantity_added += quantity_to_add
        # Note: quantity_remaining_at_cells is live available in cells, do not change it here
        district_inventory.save()

        return district_inventory

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
