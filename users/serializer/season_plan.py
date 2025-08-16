from rest_framework import serializers
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from django.utils import timezone
from report.models import Land
from users.models.addresses import Cell
from users.models.products import Product
from rest_framework.permissions import SAFE_METHODS


class CellSeasonPlanSerializer(serializers.ModelSerializer):
    sector_name = serializers.CharField(source="sector.name", read_only=True)
    district_name = serializers.CharField(source="sector.district.name", read_only=True)
    planned_crop_name = serializers.CharField(source="planned_crop.name", read_only=True)

    class Meta:
        model = Cell
        fields = [
            "uuid", "name", "sector_name", "district_name",
            "season", "season_year", "planned_crop", "planned_crop_name",
            "planned_livestock", "hectares"
        ]
        read_only_fields = ["uuid", "name", "sector_name", "district_name", "hectares"]

    def to_representation(self, instance):
        user = self.context['request'].user

        # Citizens only see cells if their land has planned_crop
        if user.user_level == "citizen":
            if not instance.planned_crop:
                raise NotFound("No planned crop found for your land's cell.")

        # District officers and super admins see all cells only if planned_crop is not null
        if user.user_level in ["district_officer", "super_admin"]:
            if not instance.planned_crop:
                raise NotFound("No planned crop found for this cell.")

        return super().to_representation(instance)

    def validate(self, data):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            raise ValidationError("Authentication credentials were not provided.")

        cell = None

        if user.user_level == "cell_officer":
            # Get the cell assigned to this cell officer
            try:
                cell = user.managed_cell
            except Cell.DoesNotExist:
                raise ValidationError("You are not assigned to any cell.")
            self.instance = cell  # override instance to assigned cell

        elif user.user_level == "citizen":
            # Citizen must provide land_id in data or query params
            land_id = data.get("land_id") or (request.query_params.get("land_id") if request else None)
            if not land_id:
                raise ValidationError({"land_id": "This field is required for citizens."})
            try:
                land = Land.objects.select_related("cell").get(pk=land_id, owner=user)
            except Land.DoesNotExist:
                raise ValidationError({"land_id": "Invalid land or you do not own this land."})
            cell = land.cell
            self.instance = cell  # override instance to linked cell

        else:
            # Other users can only perform safe methods
            if request.method not in SAFE_METHODS:
                raise ValidationError("You do not have permission to modify this resource.")
            cell = self.instance  # use current instance for safe methods

        if not cell:
            raise ValidationError("No cell information available.")

        # Unsafe method validations
        if request.method not in SAFE_METHODS:
            now = timezone.now()
            current_season = Cell.get_current_season(now)
            current_year = Cell.get_current_season_year(now)

            target_season = data.get("season", getattr(cell, "season", None))
            target_year = data.get("season_year", getattr(cell, "season_year", None))

            # Check permission: only super_admin or assigned cell_officer can modify
            if not (user.is_super_admin or (user.user_level == "cell_officer" and cell.cell_officer == user)):
                raise PermissionDenied("Only the assigned cell officer or super admin can modify this plan.")

            # Check if trying to modify current season plan
            if str(target_season) == str(current_season) and int(target_year) == int(current_year):
                if cell.planned_crop is not None:
                    raise ValidationError("Cannot modify plan for the season that has already started and has a planned crop.")
                # else: allow creating initial plan for current season

            # Restrict to next two seasons or initial current season plan
            allowed_seasons = self._get_next_two_seasons(current_season, current_year)
            if (str(target_season), int(target_year)) not in allowed_seasons and not (
                str(target_season) == str(current_season) and int(target_year) == int(current_year) and cell.planned_crop is None
            ):
                raise ValidationError("You can only create/modify plans for the next two upcoming seasons or initial plan for the current season.")

            # planned_crop must be provided and valid
            planned_crop = data.get("planned_crop")
            if not planned_crop:
                raise ValidationError({"planned_crop": "This field is required and cannot be null when creating or updating a plan."})

            # Check planned_crop category
            if isinstance(planned_crop, Product):
                prod = planned_crop
            else:
                prod = Product.objects.filter(pk=planned_crop).first()
            if not prod:
                raise ValidationError({"planned_crop": "Planned crop does not exist."})
            if prod.category != "crops":
                raise ValidationError({"planned_crop": "Planned crop should be of category 'crops'."})

        return data

    def update(self, instance: Cell, validated_data):
        for field in ["season", "season_year", "planned_crop", "planned_livestock"]:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()
        return instance

    def _get_next_two_seasons(self, current_season, current_year):
        seasons = ["A", "B", "C"]
        try:
            idx = seasons.index(str(current_season))
        except ValueError:
            idx = 0

        next1 = seasons[(idx + 1) % 3]
        next1_year = current_year if idx < 2 else current_year + 1

        next2 = seasons[(idx + 2) % 3]
        next2_year = current_year if idx < 1 else current_year + 1

        return [(next1, int(next1_year)), (next2, int(next2_year))]
