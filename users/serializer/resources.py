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

from rest_framework import serializers

class DistrictInventorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)
    
    # Expose all relevant quantities
    quantity_remaining = serializers.SerializerMethodField()
    quantity_at_cell = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    quantity_remaining_at_cells = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = DistrictInventory
        fields = [
            "id",
            "district",
            "district_name",
            "product",
            "product_name",
            "quantity_remaining",           # remaining in district
            "quantity_at_cell",             # allocated to cells
            "quantity_remaining_at_cells",  # remaining at cells after farmer allocations
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at", "quantity_at_cell", "quantity_remaining_at_cells"]

    def get_quantity_remaining(self, obj):
        return obj.quantity_remaining

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
    land_size = serializers.CharField(source='land.size_hectares', read_only=True)
    land_upi = serializers.CharField(source='land.upi', read_only=True)
    cell = serializers.CharField(source='land.cell', read_only=True)
    sector = serializers.CharField(source='land.sector', read_only=True)
    district = serializers.CharField(source='land.district', read_only=True)
    province = serializers.CharField(source='land.province', read_only=True)
    cell_name = serializers.CharField(source='land.cell.name', read_only=True)
    sector_name = serializers.CharField(source='land.sector.name', read_only=True)
    district_name = serializers.CharField(source='land.district.name', read_only=True)
    province_name = serializers.CharField(source='land.province.name', read_only=True)
    village_name = serializers.CharField(source='land.village.name', read_only=True)
    village = serializers.CharField(source='land.village', read_only=True)
    cell_id = serializers.CharField(source='land.cell.id', read_only=True)

    warnings = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = ResourceRequest
        fields = [
            "id", "farmer", "land", "livestock", "product", "quantity_requested",
            "price_per_unit", "total_price", "status", "request_date",
            "approved_by", "delivery_date", "farmer_name", "product_name",
            "phone_number", "comment", "approved_admin", "warnings", "land_size", "land_upi", "cell", "sector", "district", "province", "cell_name", "sector_name", "district_name", "province_name", "cell_id", "village", "village_name"
        ]
        read_only_fields = [
            "id", "price_per_unit", "total_price", "status", "request_date",
            "approved_by", "delivery_date", "farmer_name", "product_name",
            "phone_number", "comment", "approved_admin", "warnings", "land_size", "land_upi"
        ]

    def validate_quantity_requested(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Quantity requested must be positive.")
        return value

    # ---------- helpers ----------
    def _resolve_land(self, land):
        if not land:
            return None
        try:
            return Land.objects.select_related(
                "cell", "cell__sector", "cell__sector__district"
            ).get(pk=getattr(land, "pk", land))
        except Land.DoesNotExist:
            raise serializers.ValidationError({"land": "Associated land does not exist."})

    def _ensure_cell(self, land):
        if land and not land.cell:
            raise serializers.ValidationError(
                {"land": "User does not have an associated land with a valid cell."}
            )

    def _lookup_price(self, product, land):
        if not product or not land:
            return None
        pp = (
            ProductPrice.objects.filter(product=product, cell=land.cell).first()
            or ProductPrice.objects.filter(product=product, sector=land.cell.sector).first()
            or ProductPrice.objects.filter(product=product, district=land.cell.sector.district).first()
        )
        return pp.price if pp else None

    def _auto_or_require_quantity(self, product, land, quantity_requested, livestock=None):
        if quantity_requested is not None:
            return quantity_requested

        # For land, try to compute from recommended quantity
        if land:
            recommended = RecommendedQuantity.objects.filter(
                product=product,
                crop_name=product.name
            ).first()
            if recommended and land.size_hectares:
                return (Decimal(land.size_hectares) * Decimal(recommended.quantity_per_hectare)).quantize(Decimal("0.0001"))

        # For livestock, quantity must be provided by user
        if livestock:
            raise serializers.ValidationError({
                "quantity_requested": "Quantity is required for livestock requests."
            })

        raise serializers.ValidationError({
            "quantity_requested": "Quantity requested could not be determined."
        })

    def _maybe_add_planned_crop_warning(self, land, product):
        self._warnings = getattr(self, "_warnings", [])
        if not land or not land.cell or not product:
            return
        planned_crop = getattr(land.cell, "planned_crop", None)
        if planned_crop and planned_crop != product:
            now = timezone.now()
            current_season = land.cell.get_current_season(now)
            current_year = land.cell.get_current_season_year(now)
            if land.cell.season == current_season and land.cell.season_year == current_year:
                self._warnings.append(
                    f"Default crop for season {current_season} {current_year} in cell {land.cell.name} "
                    f"is {planned_crop.name}, but a different product was requested."
                )

    def validate(self, data):
        self._warnings = []

        land = data.get("land")
        livestock = data.get("livestock")
        product = data.get("product")

        if not land and not livestock:
            raise serializers.ValidationError("Resource request must be tied to either a land or a livestock.")

        if land:
            land_obj = self._resolve_land(land)
            self._ensure_cell(land_obj)
            if product:
                self._maybe_add_planned_crop_warning(land_obj, product)

        if livestock and not product:
            raise serializers.ValidationError({"product": "Product is required for livestock requests."})

        return data

    # ---------- create ----------
    def create(self, validated_data):
        land = self._resolve_land(validated_data.get("land"))
        livestock = validated_data.get("livestock")
        product = validated_data.get("product")

        # Land auto-fill product
        if land and not product:
            planned_crop = getattr(land.cell, "planned_crop", None)
            if planned_crop:
                validated_data["product"] = planned_crop
                product = planned_crop
            else:
                raise serializers.ValidationError({
                    "product": "No product provided and no planned crop found for this land."
                })

        # Warnings
        self._maybe_add_planned_crop_warning(land, product)

        # Quantity
        validated_data["quantity_requested"] = self._auto_or_require_quantity(
            product=product,
            land=land,
            quantity_requested=validated_data.get("quantity_requested"),
            livestock=livestock
        )

        # Price
        if land:
            price = self._lookup_price(product, land)
            if price is not None:
                validated_data["price_per_unit"] = price

        # Total price
        if validated_data.get("price_per_unit") is not None:
            validated_data["total_price"] = Decimal(validated_data["price_per_unit"]) * Decimal(validated_data["quantity_requested"])

        instance = super().create(validated_data)
        instance.warnings = self._warnings
        return instance

    def update(self, instance, validated_data):
        land = self._resolve_land(validated_data.get("land", instance.land))
        livestock = validated_data.get("livestock", instance.livestock)
        product = validated_data.get("product", instance.product)

        self._maybe_add_planned_crop_warning(land, product)

        quantity_requested = validated_data.get("quantity_requested", instance.quantity_requested)
        if quantity_requested is None:
            validated_data["quantity_requested"] = self._auto_or_require_quantity(
                product=product,
                land=land,
                quantity_requested=None,
                livestock=livestock
            )

        if land:
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
    status = serializers.ChoiceField(
        choices=[("approved", "approved"), ("rejected", "rejected"), ("delivered", "delivered")]
    )
    comment = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, data):
        request_obj = self.context["request_obj"]
        request = self.context.get("request")

        if request and request.method in ("PATCH", "PUT") and "status" not in data:
            raise serializers.ValidationError({"status": "This field is required for updates."})

        new_status = data.get("status")
        if not new_status:
            return data

        if request_obj.status == "approved" and new_status == "pending":
            raise serializers.ValidationError("Cannot revert an approved request back to pending.")
        if request_obj.status == "delivered":
            raise serializers.ValidationError("Cannot change status of a delivered request.")
        if new_status == "delivered" and request_obj.status != "approved":
            raise serializers.ValidationError("Request must be approved before it can be delivered.")

        if new_status == "approved":
            product = request_obj.product
            qty = Decimal(request_obj.quantity_requested or 0)

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

            if Decimal(cell_inv.quantity_available) < qty:
                raise serializers.ValidationError(
                    f"Not enough stock in cell inventory (available {cell_inv.quantity_available}, requested {qty})."
                )
            if Decimal(district_inv.quantity_remaining_at_cells) < qty:
                raise serializers.ValidationError(
                    f"Not enough stock remaining for cells in district inventory "
                    f"(available {district_inv.quantity_remaining_at_cells}, requested {qty})."
                )

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

                # Lock inventory rows
                cell_inv = CellInventory.objects.select_for_update().get(cell=cell, product=product)
                district_inv = DistrictInventory.objects.select_for_update().get(district=district, product=product)

                # Deduct dynamically
                cell_inv.quantity_available = Decimal(cell_inv.quantity_available) - qty
                district_inv.quantity_at_cell = Decimal(district_inv.quantity_at_cell) + qty
                district_inv.quantity_remaining_at_cells = Decimal(district_inv.quantity_remaining_at_cells) - qty

                cell_inv.save(update_fields=["quantity_available"])
                district_inv.save(update_fields=["quantity_at_cell", "quantity_remaining_at_cells"])

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

            request_obj.save(update_fields=["status", "approved_by", "delivery_date", "comment"])

        return request_obj
class ResourceRequestDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceRequest
        cell_id = serializers.CharField(source='land.cell.id', read_only=True)
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
            "cell_id",


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
