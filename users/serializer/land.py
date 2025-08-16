import re
from rest_framework import serializers
from report.models import Land, HarvestReport, LivestockLocation, LivestockAnimal
from users.models import CustomUser, Product
from django.db import transaction
class LandSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.full_names', read_only=True)
    province_name = serializers.CharField(source='province.name', read_only=True)
    district_name = serializers.CharField(source='district.name', read_only=True)
    sector_name = serializers.CharField(source='sector.name', read_only=True)
    cell_name = serializers.CharField(source='cell.name', read_only=True)
    village_name = serializers.CharField(source='village.name', read_only=True)

    class Meta:
        model = Land
        fields = [
            'id', 'owner', 'owner_name', 'upi', 'size_hectares',
            'province', 'province_name', 'district', 'district_name',
            'sector', 'sector_name', 'cell', 'cell_name', 'village', 'village_name',
            'longitude', 'latitude', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'owner', 'owner_name', 'province_name', 'district_name',
            'sector_name', 'cell_name', 'village_name', 'created_at', 'updated_at'
        ]

    def validate_upi(self, value):
        import re
         # change this to your actual model name

        # 1. Validate format
        pattern = r'^\d{1,2}/\d{2}/\d{2}/\d{2}/\d+$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "UPI must be in the format like 1/03/01/04/30."
            )

        # 2. Validate uniqueness in DB
        if Land.objects.filter(upi=value).exists():
            raise serializers.ValidationError("This UPI already exists in the system.")

        return value


    def validate_size_hectares(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Size in hectares must be a positive number."
            )
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['owner'] = request.user
        return super().create(validated_data)
class LivestockAnimalSerializer(serializers.ModelSerializer):
    animal = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())  # Animal ID
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = LivestockAnimal
        fields = ["animal", "quantity"]


from django.db import transaction
from rest_framework import serializers

class LivestockLocationSerializer(serializers.ModelSerializer):
    animals = LivestockAnimalSerializer(many=True, required=True, source='livestock_animals')
    products = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), many=True, required=False
    )

    owner_name = serializers.CharField(source='owner.full_names', read_only=True)
    province_name = serializers.CharField(source='province.name', read_only=True)
    district_name = serializers.CharField(source='district.name', read_only=True)
    sector_name = serializers.CharField(source='sector.name', read_only=True)
    cell_name = serializers.CharField(source='cell.name', read_only=True)
    village_name = serializers.CharField(source='village.name', read_only=True)
    product_names = serializers.SerializerMethodField()
    animal_names = serializers.SerializerMethodField()

   
    class Meta:
        model = LivestockLocation
        fields = [
            'id', 'owner', 'owner_name', 'province', 'province_name',
            'district', 'district_name', 'sector', 'sector_name',
            'cell', 'cell_name', 'village', 'village_name',
            'animals', 'products', 'product_names', 'animal_names', 'longitude', 'latitude',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'owner', 'owner_name', 'province_name', 
            'district_name', 'sector_name', 'cell_name',
            'village_name', 'created_at', 'updated_at', 'product_names', 'animal_names'
        ]

    def get_product_names(self, obj):
        return [product.name for product in obj.products.all()]

    def get_animal_names(self, obj):
        return [la.animal.name for la in obj.livestock_animals.all()]

    def validate(self, data):
        if not data.get("livestock_animals"):
            raise serializers.ValidationError("You must provide at least one animal with quantity.")
        return data

    def create(self, validated_data):
        livestock_animals_data = validated_data.pop("livestock_animals")
        products_data = validated_data.pop("products", [])
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["owner"] = request.user

        with transaction.atomic():
            location = LivestockLocation.objects.create(**validated_data)

            # Create animal records with quantities
            for animal_entry in livestock_animals_data:
                LivestockAnimal.objects.create(
                    livestock_location=location,
                    animal=animal_entry["animal"],
                    quantity=animal_entry["quantity"]
                )

            # Assign products
            if products_data:
                location.products.set(products_data)

        return location
