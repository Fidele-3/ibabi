from rest_framework import viewsets, generics, permissions, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from report.models import DistrictInventory, CellInventory, CellResourceRequest
from users.models.addresses import Cell, Sector, District
from users.models.products import Product
from users.serializer.inventory import DistrictInventorySerializer, CellInventorySerializer


class IsSuperAdminSafeOnly(permissions.BasePermission):
    """
    Superadmins can only use safe methods (GET, HEAD, OPTIONS).
    Other admins can do unsafe (POST, PUT, DELETE) but limited by their assigned district.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False

        if user.user_level == 'super_admin' and request.method not in permissions.SAFE_METHODS:
            return False
        
        if user.user_level in ['district_officer', 'cell_officer', 'super_admin']:
            return True
        
        return False



class DistrictInventoryViewSets(viewsets.ModelViewSet):
    queryset = DistrictInventory.objects.all()  # ✅ make sure imported correctly
    serializer_class = DistrictInventorySerializer
    permission_classes = [IsAuthenticated, IsSuperAdminSafeOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['district', 'product']  # ✅ these exist on model

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        
        if user.user_level == 'super_admin':
            return qs

        if user.user_level == 'district_officer':
            managed_district = getattr(user, 'managed_district', None)
            if not managed_district:
                return qs.none()
            return qs.filter(district=managed_district)

        return qs.none()


    def perform_create(self, serializer):
        user = self.request.user
        if user.user_level == 'district_officer':
            managed_district = getattr(user, 'managed_district', None)
            if not managed_district:
                raise PermissionDenied("You do not have a managed district assigned.")

            # Override district from user; ignore client input for district
            serializer.save(district=managed_district)

        else:
            raise PermissionDenied("Only district officers can create district inventories.")

    def perform_update(self, serializer):
        user = self.request.user
        if user.user_level == 'district_officer':
            managed_district = getattr(user, 'managed_district', None)
            if serializer.instance.district != managed_district:
                raise PermissionDenied("You can only update inventory in your managed district.")
        serializer.save()


class CellInventoryViewSets(viewsets.ReadOnlyModelViewSet):
    queryset = CellInventory.objects.all()
    serializer_class = CellInventorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['district', 'sector', 'cell', 'product']

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if user.user_level == 'super_admin':
            return qs  # all

        if user.user_level == 'district_officer':
            managed_district = getattr(user, 'managed_district', None)
            if not managed_district:
                return qs.none()
            return qs.filter(district=managed_district)

        if user.user_level == 'cell_officer':
            user_cell = getattr(user, 'managed_cell', None)
            if user_cell:
                return qs.filter(cell=user_cell)
            return qs.none()

        return qs.none()

class CellResourceRequestSerializer(serializers.ModelSerializer):
    cell = serializers.PrimaryKeyRelatedField(read_only=True)  # cell is read-only

    class Meta:
        model = CellResourceRequest
        fields = [
            'id', 'cell', 'product', 'quantity_requested', 'status',
            'request_date', 'approved_by', 'delivery_date', 'comment'
        ]
        read_only_fields = ['status', 'request_date', 'approved_by', 'delivery_date', 'cell']


class CellResourceRequestCreateView(generics.CreateAPIView):
    serializer_class = CellResourceRequestSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        if user.user_level != 'cell_officer':
            raise PermissionDenied("Only cell officers can create resource requests.")

        user_cell = getattr(user, 'managed_cell', None)
        if not user_cell:
            raise PermissionDenied("User has no cell assigned.")

        serializer.save(cell=user_cell)


class CellResourceRequestListView(generics.ListAPIView):
    serializer_class = CellResourceRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = CellResourceRequest.objects.all()

        if user.user_level == 'super_admin':
            return qs

        if user.user_level == 'district_officer':
            managed_district = getattr(user, 'managed_district', None)
            if managed_district is None:
                return qs.none()

            if isinstance(managed_district, str):
                try:
                    managed_district = District.objects.get(name=managed_district)
                except District.DoesNotExist:
                    return qs.none()

            return qs.filter(cell__sector__district=managed_district)

        if user.user_level == 'cell_officer':
            user_cell = getattr(user, 'managed_cell', None)
            if user_cell is None:
                return qs.none()

            if isinstance(user_cell, str):
                try:
                    user_cell = Cell.objects.get(name=user_cell)
                except Cell.DoesNotExist:
                    return qs.none()

            return qs.filter(cell=user_cell)

        return qs.none()