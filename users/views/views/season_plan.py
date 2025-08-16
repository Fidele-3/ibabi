import logging
from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django.utils import timezone
from users.models.addresses import Cell
from report.models import Land
from users.serializer.season_plan import CellSeasonPlanSerializer

logger = logging.getLogger(__name__)

class IsCellOfficerOrReadOnly(permissions.BasePermission):
    """
    Allow read-only access to all authenticated users.
    Unsafe methods allowed only for:
      - super admins (user_level == "super_admin")
      - assigned cell officers (user_level == "cell_officer")
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.user_level == "super_admin":
            return True

        return user.user_level == "cell_officer"

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.user_level == "super_admin":
            return True

        return user.user_level == "cell_officer" and obj.cell_officer == user


class CellSeasonPlanViewSet(viewsets.ModelViewSet):
    serializer_class = CellSeasonPlanSerializer
    queryset = Cell.objects.select_related("sector", "sector__district", "planned_crop")
    permission_classes = [IsCellOfficerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        now = timezone.now()
        current_season = Cell.get_current_season(now)
        current_year = Cell.get_current_season_year(now)

        if not user or not user.is_authenticated:
            logger.warning("Anonymous user -> empty queryset")
            return self.queryset.none()

        # Handle citizen/farmer
        if user.user_level == "citizen":
            land_id = self.request.query_params.get("land_id") or self.request.data.get("land_id")
            if not land_id:
                logger.warning("Citizen without land_id -> empty queryset")
                return self.queryset.none()

            try:
                land = Land.objects.select_related("cell").get(pk=land_id, owner=user)
            except Land.DoesNotExist:
                logger.warning(f"Citizen {user} does not own land {land_id}")
                return self.queryset.none()

            cell = land.cell
            return self.queryset.filter(id=cell.id)

        # Handle super admin
        if user.user_level == "super_admin":
            cell_id = self.request.query_params.get("cell_id")
            if cell_id:
                return self.queryset.filter(id=cell_id)
            # Return all cells with planned_crop for current season/year
            return self.queryset.filter(
                planned_crop__isnull=False,
                season=current_season,
                season_year=current_year
            )

        # Handle district officer
        if user.user_level == "district_officer":
            district = getattr(user, "managed_district", None)
            if not district:
                logger.warning(f"District officer {user} has no district assigned")
                return self.queryset.none()

            cell_id = self.request.query_params.get("cell_id")
            base_qs = self.queryset.filter(sector__district=district)
            if cell_id:
                return base_qs.filter(id=cell_id)
            return base_qs.filter(
                planned_crop__isnull=False,
                season=current_season,
                season_year=current_year
            )

        # Handle cell officer
        if user.user_level == "cell_officer":
            return self.queryset.filter(cell_officer=user)

        # Sector officer
        if user.user_level == "sector_officer":
            sector = getattr(user, "managed_sector", None)
            if sector:
                return self.queryset.filter(sector=sector)

        # Other users no access
        return self.queryset.none()

    def get_object(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication credentials were not provided.")

        if user.user_level == "super_admin":
            return super().get_object()

        if user.user_level == "cell_officer":
            try:
                return Cell.objects.get(cell_officer=user)
            except Cell.DoesNotExist:
                raise PermissionDenied("No cell assigned to this cell officer.")
            except Cell.MultipleObjectsReturned:
                return Cell.objects.filter(cell_officer=user).first()

        return super().get_object()

    def create(self, request, *args, **kwargs):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=401)

        if user.user_level not in ("super_admin", "cell_officer"):
            return Response({"detail": "Only super_admin and cell_officer can create new cell plans."}, status=403)

        return super().create(request, *args, **kwargs)
