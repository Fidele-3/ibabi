from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from report.models import DistrictInventory, CellInventory, ResourceRequest, ResourceRequestFeedback
from users.serializer.resources import (
    DistrictInventorySerializer,
    CellInventorySerializer,
    ResourceRequestSerializer,
    ResourceRequestFeedbackSerializer,
)

class IsAuthorizedUser(permissions.BasePermission):
    """
    Allow only authenticated users.
    You can customize further by user_level.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

class DistrictInventoryViewSet(viewsets.ModelViewSet):
    queryset = DistrictInventory.objects.all()
    serializer_class = DistrictInventorySerializer
    permission_classes = [IsAuthorizedUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['district', 'product']
    ordering_fields = ['updated_at', 'quantity_available']

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if hasattr(user, 'user_level'):
            if user.user_level == 'district_officer' and hasattr(user, 'managed_district'):
                if user.managed_district:
                    qs = qs.filter(district=user.managed_district)
            elif user.user_level == 'cell_officer' and hasattr(user, 'managed_cell'):
                if user.managed_cell:
                    qs = qs.filter(district=user.managed_cell.sector.district)
            elif user.user_level == 'farmer':
                # Farmers typically shouldn't access district inventory
                qs = qs.none()
        return qs

class CellInventoryViewSet(viewsets.ModelViewSet):
    queryset = CellInventory.objects.all()
    serializer_class = CellInventorySerializer
    permission_classes = [IsAuthorizedUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['district', 'sector', 'cell', 'product']
    ordering_fields = ['updated_at', 'quantity_available']

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if hasattr(user, 'user_level'):
            if user.user_level == 'cell_officer' and hasattr(user, 'managed_cell'):
                if user.managed_cell:
                    qs = qs.filter(cell=user.managed_cell)
            elif user.user_level == 'district_officer' and hasattr(user, 'managed_district'):
                if user.managed_district:
                    qs = qs.filter(district=user.managed_district)
            elif user.user_level == 'farmer':
                # Farmers typically shouldn't access cell inventory
                qs = qs.none()
        return qs

class ResourceRequestViewSet(viewsets.ModelViewSet):
    queryset = ResourceRequest.objects.all()
    serializer_class = ResourceRequestSerializer
    permission_classes = [IsAuthorizedUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['farmer', 'land', 'product', 'status']
    ordering_fields = ['request_date', 'status']

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if hasattr(user, 'user_level'):
            if user.user_level == 'farmer':
                qs = qs.filter(farmer=user)
            elif user.user_level == 'cell_officer' and hasattr(user, 'managed_cell'):
                if user.managed_cell:
                    qs = qs.filter(land__cell=user.managed_cell)
            elif user.user_level == 'district_officer' and hasattr(user, 'managed_district'):
                if user.managed_district:
                    qs = qs.filter(land__cell__sector__district=user.managed_district)
            # Admin or other roles see all
        return qs

class ResourceRequestFeedbackViewSet(viewsets.ModelViewSet):
    queryset = ResourceRequestFeedback.objects.all()
    serializer_class = ResourceRequestFeedbackSerializer
    permission_classes = [IsAuthorizedUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['farmer', 'request']
    ordering_fields = ['submitted_at']

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if hasattr(user, 'user_level'):
            if user.user_level == 'farmer':
                qs = qs.filter(farmer=user)
            # Officers and admins see all
        return qs
