from rest_framework.permissions import BasePermission
from users.models import CustomUser
from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from users.serializer.create_admin import AdminCreateSerializer
from admn.models import AdminHierarchy
from users.models.addresses import District, Sector, Cell


from rest_framework import permissions as drf_permissions

class RoleBasedPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # super_admin & district_officer: allow all methods
        if request.user.user_level in ["super_admin", "district_officer"]:
            return True

        # others: read-only
        return request.method in drf_permissions.SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        if request.user.user_level == "super_admin":
            return True

        if isinstance(obj, AdminHierarchy):
            return obj.added_by == request.user

        if isinstance(obj, CustomUser):
            return AdminHierarchy.objects.filter(admin=obj, added_by=request.user).exists()

        return False




class BaseAdminCreateViewSet(viewsets.ModelViewSet):
    serializer_class = AdminCreateSerializer
    permission_classes = [permissions.IsAuthenticated, RoleBasedPermission]
    user_level = None  # to be defined in subclass

    def get_queryset(self):
        qs = CustomUser.objects.filter(user_level=self.user_level)

        # Superadmin scope expansion
        if self.request.user.user_level == "super_admin":
            district_id = self.request.query_params.get("district_id")
            sector_id = self.request.query_params.get("sector_id")

            if self.user_level == "sector_officer" and district_id:
                qs = qs.filter(
                    id__in=Sector.objects.filter(district_id=district_id).values_list("sector_officer", flat=True)
                )

            if self.user_level == "cell_officer" and sector_id:
                qs = qs.filter(
                    id__in=Cell.objects.filter(sector_id=sector_id).values_list("cell_officer", flat=True)
                )

            return qs

        # For non-superadmins, only show admins they added
        return CustomUser.objects.filter(
            id__in=AdminHierarchy.objects.filter(added_by=self.request.user)
            .values_list("admin_id", flat=True)
        )

    def perform_create(self, serializer):
        if not self.user_level:
            raise ValueError("user_level must be defined in subclass.")

        user = serializer.save(user_level=self.user_level)

        AdminHierarchy.objects.create(
            added_by=self.request.user,
            admin=user
        )



class DistrictOfficerViewSet(BaseAdminCreateViewSet):
    user_level = "district_officer"

    def get_queryset(self):
        if self.request.user.user_level != 'super_admin':
            raise PermissionDenied("Only Super Admin can view District Officers.")
        return CustomUser.objects.filter(user_level='district_officer')

    def perform_create(self, serializer):
        if self.request.user.user_level != 'super_admin':
            raise PermissionDenied("Only Super Admin can create District Officers.")

        managed_district_id = self.request.data.get('managed_district_id')
        if not managed_district_id:
            raise ValidationError({"managed_district_id": "This field is required."})

        # Validate district before creating user
        try:
            district = District.objects.get(id=managed_district_id)
        except District.DoesNotExist:
            raise ValidationError({"managed_district_id": "Invalid district id."})

        if district.district_officer is not None:
            raise ValidationError({"managed_district_id": "This district already has a district officer."})

        # Now create user (serializer.save)
        user = serializer.save(user_level=self.user_level)

        # Assign district officer
        district.district_officer = user
        district.save()

        AdminHierarchy.objects.create(
            added_by=self.request.user,
            admin=user
        )




class SectorOfficerViewSet(BaseAdminCreateViewSet):
    user_level = "sector_officer"

    def perform_create(self, serializer):
        if self.request.user.user_level != 'district_officer':
            raise PermissionDenied("Only District Officers can create Sector Officers.")

        managed_sector_id = self.request.data.get('managed_sector_id')
        if not managed_sector_id:
            raise ValidationError({"managed_sector_id": "This field is required."})

        # Get the sector and check if it's inside the district managed by the current district_officer
        try:
            sector = Sector.objects.get(id=managed_sector_id)
        except Sector.DoesNotExist:
            raise ValidationError({"managed_sector_id": "Invalid sector id."})

        # Check if sector belongs to district_officer's district
        if sector.district.district_officer != self.request.user:
            raise PermissionDenied("You can only create Sector Officers within your own district.")

        if sector.sector_officer is not None:
            raise ValidationError({"managed_sector_id": "This sector already has a sector officer."})

        user = serializer.save(user_level=self.user_level)

        sector.sector_officer = user
        sector.save()

        AdminHierarchy.objects.create(
            added_by=self.request.user,
            admin=user
        )



class CellOfficerViewSet(BaseAdminCreateViewSet):
    user_level = "cell_officer"

    def perform_create(self, serializer):
        user_level = self.request.user.user_level
        if user_level not in ['district_officer', 'sector_officer']:
            raise PermissionDenied("Only District Officers or Sector Officers can create Cell Officers.")

        managed_cell_id = self.request.data.get('managed_cell_id')
        if not managed_cell_id:
            raise ValidationError({"managed_cell_id": "This field is required."})

        try:
            cell = Cell.objects.get(id=managed_cell_id)
        except Cell.DoesNotExist:
            raise ValidationError({"managed_cell_id": "Invalid cell id."})

        # Check ownership based on creator's user_level
        if user_level == 'district_officer':
            if cell.sector.district.district_officer != self.request.user:
                raise PermissionDenied("You can only create Cell Officers within your own district.")
        elif user_level == 'sector_officer':
            if cell.sector.sector_officer != self.request.user:
                raise PermissionDenied("You can only create Cell Officers within your own sector.")

        if cell.cell_officer is not None:
            raise ValidationError({"managed_cell_id": "This cell already has a cell officer."})

        user = serializer.save(user_level=self.user_level)

        cell.cell_officer = user
        cell.save()

        AdminHierarchy.objects.create(
            added_by=self.request.user,
            admin=user
        )



class TechnicianViewSet(BaseAdminCreateViewSet):
    user_level = "technician"

    def get_queryset(self):
        return CustomUser.objects.filter(user_level='technician')

    def perform_create(self, serializer):
        if self.request.user.user_level != 'super_admin':
            raise PermissionDenied("Only Super Admin can create Technicians.")
        super().perform_create(serializer)
