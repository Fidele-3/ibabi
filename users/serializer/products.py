from rest_framework import serializers
from report.models import Product, HarvestReport, LivestockProduction, LivestockLocation, Land
from users.models import ProductPrice, RecommendedQuantity

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

    def validate(self, data):
        user = self.context['request'].user

        # Only super admins can create/update products
        if not getattr(user, 'is_super_admin', False):
            # Disallow create/update for non-superadmins
            if self.instance is None or self.instance.pk is None:
                raise serializers.ValidationError("Only super admins can create products.")
            else:
                raise serializers.ValidationError("Only super admins can update products.")

        # Validate required fields are present for creation or update
        required_fields = ['name', 'unit', 'category', 'description']  # Adjust fields to your model's required fields
        missing = [f for f in required_fields if f not in data or data.get(f) in (None, '')]
        if missing:
            raise serializers.ValidationError(f"Missing required fields for product: {', '.join(missing)}")

        return data


class ProductPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPrice
        fields = '__all__'

    def validate(self, data):
        user = self.context['request'].user
        if not getattr(user, 'is_super_admin', False):
            raise serializers.ValidationError("Only super admins can create or update product prices.")

        # Example validation: price must be positive
        price = data.get('price')
        if price is None or price <= 0:
            raise serializers.ValidationError("Price must be a positive number.")

        return data


class RecommendedQuantitySerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendedQuantity
        fields = '__all__'

    def validate(self, data):
        user = self.context['request'].user
        if not getattr(user, 'is_super_admin', False):
            raise serializers.ValidationError("Only super admins can create or update recommended quantities.")

        qty = data.get('quantity_per_hectare')
        if qty is None or qty <= 0:
            raise serializers.ValidationError("Quantity per hectare must be a positive number.")

        return data


class HarvestReportSerializer(serializers.ModelSerializer):
    # Readable fields for frontend
    farmer_names = serializers.CharField(source='farmer.get_full_name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)
    product_type = serializers.CharField(source='product.category', read_only=True)

    land_size = serializers.CharField(source='land.size_hectares', read_only=True)
    land_district_location = serializers.CharField(source='land.district.name', read_only=True)
    land_sector_location = serializers.CharField(source='land.sector.name', read_only=True)
    land_cell_location = serializers.CharField(source='land.cell.name', read_only=True)
    land_village_location = serializers.CharField(source='land.village.name', read_only=True)
    land_upi = serializers.CharField(source='land.upi', read_only=True)
    latitude = serializers.FloatField(source='land.cell.latitude', read_only=True)
    longitude = serializers.FloatField(source='land.cell.longitude', read_only=True)

    # Explicit fields farmer must select
    land = serializers.PrimaryKeyRelatedField(queryset=Land.objects.all())
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())

    class Meta:
        model = HarvestReport
        fields = [
            'id', 'farmer', 'farmer_names',
            'land', 'product',
            'product_name', 'product_unit', 'product_type',
            'land_size', 'land_district_location', 'land_sector_location',
            'land_cell_location', 'land_village_location',
            'quantity', 'report_date', 'land_upi', 'status', 'latitude', 'longitude'
        ]
        read_only_fields = ['farmer', 'report_date', 'land_size',
                            'land_district_location', 'land_sector_location',
                            'land_cell_location', 'land_village_location',
                            'product_name', 'product_unit', 'product_type']

    def validate(self, data):
        user = self.context['request'].user

        # Require land
        if not data.get("land"):
            raise serializers.ValidationError({
                "land": "Please select a land. This field is required."
            })
        if not data.get("status"):
            raise serializers.ValidationError({
                "status": "Please select a status. This field is required."
            })

        # Require product
        if not data.get("product"):
            raise serializers.ValidationError({
                "product": "Please select a product. This field is required."
            })

        # Farmers can only update their own reports
        if self.instance and self.instance.farmer != user:
            raise serializers.ValidationError(
                "You can only modify your own harvest reports."
            )

        # Ensure land belongs to farmer
        if data.get("land") and data["land"].owner != user:
            raise serializers.ValidationError(
                "You can only report harvests from your own land."
            )

        # Quantity validation
        if data.get("quantity") is not None and data["quantity"] <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")

        return data

    def create(self, validated_data):
        validated_data['farmer'] = self.context['request'].user
        return super().create(validated_data)





class LivestockProductionSerializer(serializers.ModelSerializer):
    # Readable fields for frontend
    farmer_names = serializers.CharField(source='farmer.get_full_name', read_only=True)
    livestock_name = serializers.CharField(source='product.name', read_only=True)
    livestock_category = serializers.CharField(source='product.category', read_only=True)
    livestock_district_location = serializers.CharField(source='location.district.name', read_only=True)
    livestock_sector_location = serializers.CharField(source='location.sector.name', read_only=True)
    livestock_cell_location = serializers.CharField(source='location.cell.name', read_only=True)
    livestock_village_location = serializers.CharField(source='location.village.name', read_only=True)
    animals = serializers.SerializerMethodField()
    
    # Alias DB field `location` as `livestock` for frontend
    livestock = serializers.PrimaryKeyRelatedField(
        source='location',  # maps to actual DB field
        queryset=LivestockLocation.objects.all()
    )

    # Product must also be explicitly selected by user
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all()
    )
    latitude = serializers.FloatField(source='location.cell.latitude', read_only=True)
    longitude = serializers.FloatField(source='location.cell.longitude', read_only=True)


    class Meta:
        model = LivestockProduction
        fields = [
            'id', 'farmer', 'farmer_names', 'status',
            'livestock', 'product',  # frontend sees these
            'livestock_name', 'livestock_category',
            'animals', 'quantity', 'report_date',
            'livestock_district_location', 'livestock_sector_location',
            'livestock_cell_location', 'livestock_village_location', 'latitude', 'longitude'
        ]
        read_only_fields = ['farmer']

    def get_animals(self, obj):
        return [
            {
                "animal_id": la.animal.id,
                "animal_name": la.animal.name,
                "quantity": la.quantity
            }
            for la in obj.location.livestock_animals.all()
        ]

    def validate(self, data):
        user = self.context['request'].user

        # Require livestock
        if not data.get("location"):
            raise serializers.ValidationError({
                "livestock": "Please select a livestock. This field is required."
            })
        if not data.get("status"):
            raise serializers.ValidationError({
                "status": "Please select a status. This field is required."
            })

        # Require product
        if not data.get("product"):
            raise serializers.ValidationError({
                "product": "Please select a product. This field is required."
            })

        # Farmers can only create/update their own livestock production reports
        if self.instance and self.instance.farmer != user:
            raise serializers.ValidationError(
                "You can only modify your own livestock production reports."
            )

        # Ensure the selected livestock belongs to the farmer
        if data.get("location") and data["location"].owner != user:
            raise serializers.ValidationError(
                "You can only report production for your own livestock."
            )

        # Quantity validation
        if data.get("quantity") is not None and data["quantity"] <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")

        return data

    def create(self, validated_data):
        validated_data['farmer'] = self.context['request'].user
        return super().create(validated_data)
