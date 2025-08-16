from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from report.models import (
    DistrictInventory,
    CellInventory,
    ResourceRequest,
    ProductPrice,
    RecommendedQuantity,
    ResourceRequestFeedback,
)
from users.models import CustomUser
from report.models import Land

class DistrictInventorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)
    quantity_available = serializers.SerializerMethodField()  # expose property as a field

    class Meta:
        model = DistrictInventory
        fields = [
            "id",
            "district",
            "district_name",
            "product",
            "product_name",
            "quantity_available",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

    def get_quantity_available(self, obj):
        return obj.quantity_remaining  # map to model property



class CellInventorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    cell_name = serializers.CharField(source="cell.name", read_only=True)
    sector_name = serializers.CharField(source="sector.name", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)

    class Meta:
        model = CellInventory
        fields = [
            "id",
            "cell",
            "cell_name",
            "sector",
            "sector_name",
            "district",
            "district_name",
            "product",
            "product_name",
            "quantity_available",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

    def validate(self, data):
        # Only quantity can be set here
        return data



from decimal import Decimal
from django.utils import timezone
from rest_framework import serializers

class ResourceRequestSerializer(serializers.ModelSerializer):
    farmer = serializers.HiddenField(default=serializers.CurrentUserDefault())
    price_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_price = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    status = serializers.CharField(read_only=True)
    approved_by = serializers.PrimaryKeyRelatedField(read_only=True)
    delivery_date = serializers.DateTimeField(read_only=True)
    request_date = serializers.DateTimeField(read_only=True)
    farmer_name = serializers.CharField(source='farmer.get_full_name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    phone_number = serializers.CharField(source='farmer.phone_number', read_only=True)
    approved_admin = serializers.CharField(source='approved_by.get_full_name', read_only=True)

    # Non-blocking messages
    warnings = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = ResourceRequest
        fields = [
            "id", "farmer", "land", "product", "quantity_requested",
            "price_per_unit", "total_price", "status", "request_date",
            "approved_by", "delivery_date", "farmer_name", "product_name",
            "phone_number", "comment", "approved_admin", "warnings"
        ]
        read_only_fields = [
            "id", "price_per_unit", "total_price", "status", "request_date",
            "approved_by", "delivery_date", "farmer_name", "product_name",
            "phone_number", "comment", "approved_admin", "warnings"
        ]

    def validate_quantity_requested(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Quantity requested must be positive.")
        return value

    # ---------- helpers ----------
    def _resolve_land(self, land):
        from report.models import Land  # adjust import path if needed
        if not land:
            raise serializers.ValidationError({"land": "User must specify a land."})
        try:
            return Land.objects.select_related(
                "cell", "cell__sector", "cell__sector__district"
            ).get(pk=getattr(land, "pk", land))
        except Land.DoesNotExist:
            raise serializers.ValidationError({"land": "Associated land does not exist."})

    def _ensure_cell(self, land):
        if not land.cell:
            raise serializers.ValidationError(
                {"land": "User does not have an associated land with a valid cell."}
            )

    def _lookup_price(self, product, land):
        # adjust import path
        pp = (
            ProductPrice.objects.filter(product=product, cell=land.cell).first()
            or ProductPrice.objects.filter(product=product, sector=land.cell.sector).first()
            or ProductPrice.objects.filter(product=product, district=land.cell.sector.district).first()
        )
        return pp.price if pp else None

    def _auto_or_require_quantity(self, product, land, quantity_requested):
        """
        If quantity is provided, return it.
        Else, try to compute from RecommendedQuantity * land.size_hectares.
        If not possible, raise ValidationError requiring user input.
        """
        if quantity_requested is not None:
            return quantity_requested


        recommended = RecommendedQuantity.objects.filter(
            product=product,
            crop_name=product.name  # keep your existing matching rule
        ).first()

        if recommended and land.size_hectares:
            return (Decimal(land.size_hectares) * Decimal(recommended.quantity_per_hectare)).quantize(Decimal("0.0001"))

        # Hard requirement: we cannot leave it null
        raise serializers.ValidationError({
            "quantity_requested": (
                f"Please provide 'quantity_requested'. "
                f"No recommended quantity found for '{product.name}' "
                f"or land size is missing to auto-compute."
            )
        })

    def _maybe_add_planned_crop_warning(self, land, product):
        self._warnings = getattr(self, "_warnings", [])
        planned_crop = getattr(land.cell, "planned_crop", None)
        if not (product and planned_crop and planned_crop != product):
            return
        now = timezone.now()
        current_season = land.cell.get_current_season(now)
        current_year = land.cell.get_current_season_year(now)
        if land.cell.season == current_season and land.cell.season_year == current_year:
            self._warnings.append(
                f"Default crop for season {current_season} {current_year} in cell {land.cell.name} "
                f"is {planned_crop.name}, but a different product was requested."
            )

    def validate(self, data):
        # prepare warnings container
        self._warnings = []
        land = data.get("land")
        product = data.get("product")

        # We only do soft checks here; hard requirements handled in create/update
        if land:
            land_obj = self._resolve_land(land)
            self._ensure_cell(land_obj)
            if product:
                self._maybe_add_planned_crop_warning(land_obj, product)

        return data

    # ---------- create ----------
    def create(self, validated_data):
        # Resolve land and ensure cell
        land = self._resolve_land(validated_data.get("land"))
        self._ensure_cell(land)

        # Resolve/auto product from planned crop if missing
        product = validated_data.get("product")
        if not product:
            planned_crop = getattr(land.cell, "planned_crop", None)
            if planned_crop:
                product = planned_crop
                validated_data["product"] = product
            else:
                raise serializers.ValidationError({
                    "product": "No product provided and no planned crop found for this cell."
                })

        # Add soft warning about planned crop mismatch (non-blocking)
        self._maybe_add_planned_crop_warning(land, product)

        # Ensure/compute quantity (MUST NOT be null)
        validated_data["quantity_requested"] = self._auto_or_require_quantity(
            product=product,
            land=land,
            quantity_requested=validated_data.get("quantity_requested")
        )

        # Price per unit (optional)
        price = self._lookup_price(product, land)
        if price is not None:
            validated_data["price_per_unit"] = price

        # Total price if possible
        if validated_data.get("price_per_unit") is not None:
            validated_data["total_price"] = (
                Decimal(validated_data["price_per_unit"]) *
                Decimal(validated_data["quantity_requested"])
            )

        instance = super().create(validated_data)
        instance.warnings = self._warnings  # attach soft messages
        return instance


    def update(self, instance, validated_data):
        land = self._resolve_land(validated_data.get("land", instance.land))
        self._ensure_cell(land)

        # product might change
        product = validated_data.get("product", instance.product)

        # non-blocking warning
        self._maybe_add_planned_crop_warning(land, product)

    
        quantity_requested = validated_data.get("quantity_requested", instance.quantity_requested)
        if quantity_requested is None:
            validated_data["quantity_requested"] = self._auto_or_require_quantity(
                product=product,
                land=land,
                quantity_requested=None
            )

    
        price = self._lookup_price(product, land)
        if price is not None:
            validated_data["price_per_unit"] = price

        if "price_per_unit" in validated_data or "quantity_requested" in validated_data:
            price_val = validated_data.get("price_per_unit", instance.price_per_unit)
            qty_val = validated_data.get("quantity_requested", instance.quantity_requested)
            if price_val is not None and qty_val is not None:
                validated_data["total_price"] = Decimal(price_val) * Decimal(qty_val)

        instance = super().update(instance, validated_data)
        instance.warnings = self._warnings
        return instance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["warnings"] = getattr(instance, "warnings", [])
        return rep



class ResourceRequestStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[("approved","approved"), ("rejected","rejected"), ("delivered","delivered")])
    comment = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, data):
        request_obj = self.context["request_obj"]
        request = self.context.get("request")
        
        # Enforce 'status' is present if method is PATCH or PUT (update)
        if request and request.method in ("PATCH", "PUT") and "status" not in data:
            raise serializers.ValidationError({"status": "This field is required for updates."})

        new_status = data.get("status")
        if new_status is None:
            # If status not provided (say, for non-update requests), skip status validations
            return data



        if request_obj.status == "approved" and new_status == "pending":
            raise serializers.ValidationError("Cannot revert an approved request back to pending.")

        if request_obj.status == "delivered":
            raise serializers.ValidationError("Cannot change status of a delivered request.")

        if new_status == "delivered" and request_obj.status != "approved":
            raise serializers.ValidationError("Request must be approved before it can be delivered.")

        if new_status == "approved":
            product = request_obj.product
            qty = request_obj.quantity_requested or 0

            if not product:
                raise serializers.ValidationError("Cannot approve request with no product set.")

            cell = request_obj.land.cell
            district = cell.sector.district

            cell_inv = CellInventory.objects.filter(cell=cell, product=product).first()
            district_inv = DistrictInventory.objects.filter(district=district, product=product).first()

            if not cell_inv:
                raise serializers.ValidationError(f"Product '{product.name}' not available in cell inventory.")
            if not district_inv:
                raise serializers.ValidationError(f"Product '{product.name}' not available in district inventory.")
            if cell_inv.quantity_available < qty:
                raise serializers.ValidationError(f"Not enough stock in cell inventory (available {cell_inv.quantity_available}, requested {qty}).")
            if district_inv.quantity_remaining < qty:
                raise serializers.ValidationError(f"Not enough stock in district inventory (available {district_inv.quantity_remaining}, requested {qty}).")

        return data

    def save(self, **kwargs):
        request_obj = self.context["request_obj"]
        new_status = self.validated_data["status"]
        comment = self.validated_data.get("comment", "")

        with transaction.atomic():
            if new_status == "approved":
                product = request_obj.product
                qty = Decimal(request_obj.quantity_requested or 0)
                cell = request_obj.land.cell
                district = cell.sector.district

                cell_inv_qs = CellInventory.objects.select_for_update().filter(cell=cell, product=product)
                district_inv_qs = DistrictInventory.objects.select_for_update().filter(district=district, product=product)

                cell_inv = cell_inv_qs.first()
                district_inv = district_inv_qs.first()

                if not cell_inv or not district_inv:
                    raise ValidationError("Inventory rows missing during approval check.")

                if Decimal(cell_inv.quantity_available) < qty:
                    raise ValidationError("Not enough stock in cell inventory to approve the request.")
                if Decimal(district_inv.quantity_remaining) < qty:
                    raise ValidationError("Not enough stock in district inventory to approve the request.")

                cell_inv.quantity_available = float(Decimal(cell_inv.quantity_available) - qty)
                district_inv.quantity_at_cell = float(Decimal(district_inv.quantity_at_cell) - qty)
                cell_inv.save()
                district_inv.save()

                request_obj.status = "approved"
                request_obj.approved_by = self.context["request"].user
                request_obj.comment = comment

            elif new_status == "rejected":
                request_obj.status = "rejected"
                request_obj.comment = comment

            elif new_status == "delivered":
                request_obj.status = "delivered"
                request_obj.delivery_date = timezone.now()
                request_obj.comment = comment

            request_obj.save()
        return request_obj

class ResourceRequestDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceRequest
        fields = [
            "id",
            "land",
            "product",
            "quantity_requested",
            "price_per_unit",
            "total_price",
            "status",
            "request_date",
            "approved_by",
            "delivery_date",
            "comment",
        ]
        read_only_fields = fields  # this serializer is for read-only output



class ResourceRequestFeedbackSerializer(serializers.ModelSerializer):
    farmer_email = serializers.CharField(source="farmer.email", read_only=True)
    request_id = serializers.UUIDField(source="request.id", read_only=True)

    class Meta:
        model = ResourceRequestFeedback
        fields = [
            "id",
            "request",
            "request_id",
            "farmer",
            "farmer_email",
            "rating",
            "comment",
            "submitted_at",
        ]
        read_only_fields = ["id", "submitted_at", "farmer"]
