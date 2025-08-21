import logging
import re
from rest_framework import serializers
from report.models import Land, HarvestReport, LivestockLocation, LivestockAnimal
from users.models import CustomUser, Product
from django.db import transaction
from users.models.addresses import Province, District, Sector, Cell, Village

# Create a dedicated logger for serializers
logger = logging.getLogger("serializers_debug")

class LandSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.full_names', read_only=True)
    province_name = serializers.CharField(source='province.name', read_only=True)
    district_name = serializers.CharField(source='district.name', read_only=True)
    sector_name = serializers.CharField(source='sector.name', read_only=True)
    cell_name = serializers.CharField(source='cell.name', read_only=True)
    village_name = serializers.CharField(source='village.name', read_only=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    latitude = serializers.FloatField(required=False, allow_null=True)
    planned_crop = serializers.CharField(source="cell.planned_crop.name", read_only=True)
    current_season = serializers.CharField(source="cell.season", read_only=True)



    class Meta:
        model = Land
        fields = [
            'id', 'owner', 'owner_name', 'upi', 'size_hectares',
            'province', 'province_name', 'district', 'district_name',
            'sector', 'sector_name', 'cell', 'cell_name', 'village', 'village_name',
            'longitude', 'latitude', 'created_at', 'updated_at', 'planned_crop', 'current_season'
        ]
        read_only_fields = [
            'id', 'owner', 'owner_name', 'province_name', 'district_name',
            'sector_name', 'cell_name', 'village_name', 'created_at', 'updated_at', 'planned_crop', 'current_season'
        ]

    def validate_upi(self, value):
        logger.debug(f"[VALIDATE_UPI] Checking UPI: {value}")
        pattern = r'^\d{1,2}/\d{2}/\d{2}/\d{2}/\d+$'
        if not re.match(pattern, value):
            logger.warning(f"[VALIDATE_UPI] Invalid format: {value}")
            raise serializers.ValidationError("UPI must be in the format like 1/03/01/04/30.")
        if Land.objects.filter(upi=value).exists():
            logger.warning(f"[VALIDATE_UPI] Duplicate UPI: {value}")
            raise serializers.ValidationError("This UPI already exists in the system.")
        logger.debug(f"[VALIDATE_UPI] Passed for UPI: {value}")
        return value

    def validate_size_hectares(self, value):
        logger.debug(f"[VALIDATE_SIZE] Checking size_hectares: {value}")
        if value <= 0:
            logger.warning(f"[VALIDATE_SIZE] Invalid size_hectares: {value}")
            raise serializers.ValidationError("Size in hectares must be a positive number.")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['owner'] = request.user
            logger.debug(f"[CREATE] Setting owner: {request.user}")
        logger.debug(f"[CREATE] Validated data before save: {validated_data}")
        return super().create(validated_data)
    
    def is_valid(self, raise_exception=False):
        valid = super().is_valid(raise_exception=False)
        if not valid:
            logger.debug(f"[IS_VALID] Validation errors: {self.errors}")
        if raise_exception and not valid:
            raise serializers.ValidationError(self.errors)

class LivestockAnimalSerializer(serializers.ModelSerializer):
    animal = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = LivestockAnimal
        fields = ["animal", "quantity"]





class LivestockProductSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class LivestockLocationSerializer(serializers.ModelSerializer):
    upi = serializers.CharField(required=True)  # Make UPI required

    livestock_animals = serializers.ListSerializer(
        child=serializers.DictField(
            child=serializers.CharField(),  # Accept string IDs from frontend
        ),
        write_only=True
    )

    owner_name = serializers.CharField(source="owner.full_names", read_only=True)
    province_name = serializers.CharField(source="province.name", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)
    sector_name = serializers.CharField(source="sector.name", read_only=True)
    cell_name = serializers.CharField(source="cell.name", read_only=True)
    village_name = serializers.CharField(source="village.name", read_only=True)
    

    province = serializers.PrimaryKeyRelatedField(queryset=Province.objects.all())
    district = serializers.PrimaryKeyRelatedField(queryset=District.objects.all())
    sector = serializers.PrimaryKeyRelatedField(queryset=Sector.objects.all())
    cell = serializers.PrimaryKeyRelatedField(queryset=Cell.objects.all())
    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())

    animals = serializers.SerializerMethodField()

    class Meta:
        model = LivestockLocation
        fields = [
            "id", "upi", "owner", "owner_name",
            "province", "province_name",
            "district", "district_name",
            "sector", "sector_name",
            "cell", "cell_name",
            "village", "village_name",
            "longitude", "latitude",
            "livestock_animals", "animals",
            "number_of_products",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "owner", "owner_name",
            "province_name", "district_name", "sector_name",
            "cell_name", "village_name",
            "animals", "created_at", "updated_at",
        ]

    def get_animals(self, obj):
        return [
            {"animal": la.animal.name, "quantity": la.quantity}
            for la in obj.livestock_animals.all()
        ]

    def create(self, validated_data):
        animals_data = validated_data.pop("livestock_animals", [])

        # Ensure required fields including UPI
        required_fields = ["upi", "province", "district", "sector", "cell", "village"]
        for field in required_fields:
            if field not in validated_data or validated_data[field] in [None, ""]:
                raise serializers.ValidationError({field: "This field is required."})

        # Set owner if missing
        if "owner" not in validated_data and self.context.get("request"):
            validated_data["owner"] = self.context["request"].user

        location = LivestockLocation.objects.create(**validated_data)

        total_number = 0
        errors = []

        # Handle livestock animals
        for idx, entry in enumerate(animals_data):
            animal_id = entry.get("animal")
            quantity_str = entry.get("quantity", "1")

            try:
                animal_product = Product.objects.get(id=animal_id)
            except Product.DoesNotExist:
                errors.append({f"animal_{idx}": f"Product with ID {animal_id} does not exist."})
                continue

            try:
                quantity = int(quantity_str)
                if quantity < 1:
                    raise ValueError
            except ValueError:
                errors.append({f"quantity_{idx}": f"Invalid quantity '{quantity_str}' for animal {animal_id}."})
                continue

            LivestockAnimal.objects.create(
                livestock_location=location,
                animal=animal_product,
                quantity=quantity
            )
            total_number += quantity

        location.number_of_products = total_number
        location.save()

        if errors:
            raise serializers.ValidationError(errors)

        return location

    def full_validate(self, data):
        """
        Call this in your view to validate and see detailed error messages.
        """
        serializer = LivestockLocationSerializer(data=data, context=self.context)
        if serializer.is_valid():
            return {"is_valid": True, "validated_data": serializer.validated_data}
        else:
            return {"is_valid": False, "errors": serializer.errors}
