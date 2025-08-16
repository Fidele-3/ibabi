from rest_framework import permissions
from report.models import Land
# permissions.py
from rest_framework import permissions
from report.models import Land

class LandPermission(permissions.BasePermission):
    """
    Custom permission:
    - Owners can see and manage their own lands
    - Officers see lands in their jurisdiction
    - Superadmin sees all
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj: Land):
        user = request.user

        # 1. Owners can view their own
        if user == obj.owner:
            return True

        # 2. Role based access
        if getattr(user, "user_level", None) == "super_admin":
            return True

        if getattr(user, "user_level", None) == "district_officer" and hasattr(user, "managed_district"):
            return obj.district == user.managed_district

        if getattr(user, "user_level", None) == "sector_officer" and hasattr(user, "managed_sector"):
            return obj.sector == user.managed_sector

        if getattr(user, "user_level", None) == "cell_officer" and hasattr(user, "managed_cell"):
            return obj.cell == user.managed_cell

        return False



from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from report.models import Land, LivestockLocation
from users.serializer.land import LandSerializer, LivestockLocationSerializer

class LandViewSet(viewsets.ModelViewSet):
    serializer_class = LandSerializer
    permission_classes = [LandPermission]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['province', 'district', 'sector', 'cell', 'village', 'owner']
    ordering_fields = ['created_at', 'size_hectares']

    def get_queryset(self):
        user = self.request.user
        qs = Land.objects.none()  # start empty

        if not user.is_authenticated:
            return qs

        base_qs = Land.objects.all()

        # Always include lands owned by the user
        qs = Land.objects.filter(owner=user)

        # Role-based additions
        if getattr(user, "user_level", None) == "super_admin":
            qs = base_qs

        elif getattr(user, "user_level", None) == "district_officer" and hasattr(user, "managed_district"):
            qs = qs | base_qs.filter(district=user.managed_district)

        elif getattr(user, "user_level", None) == "sector_officer" and hasattr(user, "managed_sector"):
            qs = qs | base_qs.filter(sector=user.managed_sector)

        elif getattr(user, "user_level", None) == "cell_officer" and hasattr(user, "managed_cell"):
            qs = qs | base_qs.filter(cell=user.managed_cell)

        return qs.distinct()


    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class LivestockLocationViewSet(viewsets.ModelViewSet):
    serializer_class = LivestockLocationSerializer
    permission_classes = [LandPermission]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['province', 'district', 'sector', 'cell', 'village', 'owner']
    ordering_fields = ['created_at', 'number_of_products']

    def get_queryset(self):
        user = self.request.user
        qs = LivestockLocation.objects.none()

        if not user.is_authenticated:
            return qs

        base_qs = LivestockLocation.objects.all()
        qs = LivestockLocation.objects.filter(owner=user)

        if getattr(user, "user_level", None) == "super_admin":
            qs = base_qs
        elif getattr(user, "user_level", None) == "district_officer" and hasattr(user, "managed_district"):
            qs = qs | base_qs.filter(district=user.managed_district)
        elif getattr(user, "user_level", None) == "sector_officer" and hasattr(user, "managed_sector"):
            qs = qs | base_qs.filter(sector=user.managed_sector)
        elif getattr(user, "user_level", None) == "cell_officer" and hasattr(user, "managed_cell"):
            qs = qs | base_qs.filter(cell=user.managed_cell)

        return qs.distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)