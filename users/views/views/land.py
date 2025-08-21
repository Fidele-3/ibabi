import logging
from rest_framework import permissions, viewsets, filters, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from report.models import Land, LivestockLocation
from users.serializer.land import LandSerializer, LivestockLocationSerializer

logger = logging.getLogger(__name__)

# ---------------- Permissions ----------------
class LandPermission(permissions.BasePermission):
    """
    Custom permission:
    - Owners can see and manage their own lands
    - Officers see lands in their jurisdiction
    - Superadmin sees all
    """

    def has_permission(self, request, view):
        logger.debug(f"[PERMISSION] User={request.user} Authenticated={request.user.is_authenticated}")
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj: Land):
        user = request.user
        logger.debug(f"[OBJECT PERMISSION] Checking user={user} level={getattr(user, 'user_level', None)} for land={obj.id}")

        # 1. Owners can view their own
        if user == obj.owner:
            logger.debug(f"[ALLOW] User {user} is owner of land {obj.id}")
            return True

        # 2. Superadmin
        if getattr(user, "user_level", None) == "super_admin":
            logger.debug(f"[ALLOW] User {user} is super_admin")
            return True

        # 3. District officer
        if getattr(user, "user_level", None) == "district_officer" and hasattr(user, "managed_district"):
            logger.debug(f"[CHECK] District officer={user.managed_district} vs Land district={obj.district}")
            return obj.district == user.managed_district

        # 4. Sector officer
        if getattr(user, "user_level", None) == "sector_officer" and hasattr(user, "managed_sector"):
            logger.debug(f"[CHECK] Sector officer={user.managed_sector} vs Land sector={obj.sector}")
            return obj.sector == user.managed_sector

        # 5. Cell officer
        if getattr(user, "user_level", None) == "cell_officer" and hasattr(user, "managed_cell"):
            logger.debug(f"[CHECK] Cell officer={user.managed_cell} vs Land cell={obj.cell}")
            return obj.cell == user.managed_cell

        logger.debug(f"[DENY] User {user} has no permission for land {obj.id}")
        return False


# ---------------- ViewSets ----------------
class LandViewSet(viewsets.ModelViewSet):
    serializer_class = LandSerializer
    permission_classes = [LandPermission]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['province', 'district', 'sector', 'cell', 'village', 'owner']
    ordering_fields = ['created_at', 'size_hectares']

    def get_queryset(self):
        user = self.request.user
        logger.debug(f"[LAND-GET-QUERYSET] User={user}, Level={getattr(user, 'user_level', None)}")

        qs = Land.objects.none()

        if not user.is_authenticated:
            logger.debug("[LAND-GET-QUERYSET] User not authenticated → empty queryset")
            return qs

        base_qs = Land.objects.all()
        qs = Land.objects.filter(owner=user)
        logger.debug(f"[LAND-GET-QUERYSET] User owns {qs.count()} lands")

        if getattr(user, "user_level", None) == "super_admin":
            logger.debug("[LAND-GET-QUERYSET] Superadmin → all lands")
            qs = base_qs

        elif getattr(user, "user_level", None) == "district_officer" and hasattr(user, "managed_district"):
            logger.debug(f"[LAND-GET-QUERYSET] District officer for {user.managed_district}")
            qs = qs | base_qs.filter(district=user.managed_district)

        elif getattr(user, "user_level", None) == "sector_officer" and hasattr(user, "managed_sector"):
            logger.debug(f"[LAND-GET-QUERYSET] Sector officer for {user.managed_sector}")
            qs = qs | base_qs.filter(sector=user.managed_sector)

        elif getattr(user, "user_level", None) == "cell_officer" and hasattr(user, "managed_cell"):
            logger.debug(f"[LAND-GET-QUERYSET] Cell officer for {user.managed_cell}")
            qs = qs | base_qs.filter(cell=user.managed_cell)

        logger.debug(f"[LAND-GET-QUERYSET] Returning {qs.distinct().count()} lands total")
        return qs.distinct()

    def perform_create(self, serializer):
        logger.debug(f"[LAND-CREATE] User {self.request.user} creating land with data={self.request.data}")
        land = serializer.save(owner=self.request.user)
        logger.debug(f"[LAND-CREATE] Land created id={land.id} by user={self.request.user}")
        return land



class LivestockLocationViewSet(viewsets.ModelViewSet):
    serializer_class = LivestockLocationSerializer
    permission_classes = [LandPermission]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['province', 'district', 'sector', 'cell', 'village', 'owner']
    ordering_fields = ['created_at', 'number_of_products']

    def get_queryset(self):
        user = self.request.user
        logger.debug(f"[LIVESTOCK-GET-QUERYSET] User={user}, Level={getattr(user, 'user_level', None)}")

        if not user.is_authenticated:
            logger.debug("[LIVESTOCK-GET-QUERYSET] User not authenticated → empty queryset")
            return LivestockLocation.objects.none()

        base_qs = LivestockLocation.objects.all()
        qs = LivestockLocation.objects.filter(owner=user)

        user_level = getattr(user, "user_level", None)
        if user_level == "super_admin":
            qs = base_qs
        elif user_level == "district_officer" and hasattr(user, "managed_district"):
            qs = qs | base_qs.filter(district=user.managed_district)
        elif user_level == "sector_officer" and hasattr(user, "managed_sector"):
            qs = qs | base_qs.filter(sector=user.managed_sector)
        elif user_level == "cell_officer" and hasattr(user, "managed_cell"):
            qs = qs | base_qs.filter(cell=user.managed_cell)

        logger.debug(f"[LIVESTOCK-GET-QUERYSET] Returning {qs.distinct().count()} locations total")
        return qs.distinct()

    def create(self, request, *args, **kwargs):
        logger.debug(f"[LIVESTOCK-CREATE] User {request.user} creating livestock with data={request.data}")

        serializer = LivestockLocationSerializer(context={"request": request})
        validation_result = serializer.full_validate(request.data)

        if not validation_result["is_valid"]:
            logger.error(f"[LIVESTOCK-CREATE-ERROR] Validation failed: {validation_result['errors']}")
            return Response({"errors": validation_result["errors"]}, status=status.HTTP_400_BAD_REQUEST)

        # If valid, create the location and related animals
        livestock = serializer.create(validation_result["validated_data"])
        logger.debug(f"[LIVESTOCK-CREATE] Livestock created id={livestock.id} by user={request.user}")

        response_serializer = LivestockLocationSerializer(livestock)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)