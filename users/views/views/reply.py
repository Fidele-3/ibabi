from decimal import Decimal
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.core.exceptions import ValidationError

from report.models import CellResourceRequest, CellInventory, DistrictInventory
from users.views.views.inventory import CellResourceRequestSerializer


class CellResourceRequestReplySerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(source='product.name', read_only=True)
    cell_name = serializers.CharField(source='cell.name', read_only=True)
    requester_name = serializers.CharField(source='cell.cell_officer.get_full_name', read_only=True)
    comment = serializers.CharField(allow_blank=True, required=False)

    class Meta:
        model = CellResourceRequest
        fields = ['id', 'status', 'comment', 'product_name', 'cell_name', 'requester_name', 'status']
        read_only_fields = ['id', 'product_name', 'cell_name', 'requester_name']

    def validate(self, data):
        request_obj = self.instance
        new_status = data.get('status', request_obj.status)

        # Basic status validation
        if request_obj.status == "approved" and new_status == "pending":
            raise serializers.ValidationError("Cannot revert an approved request back to pending.")
        if request_obj.status == "delivered":
            raise serializers.ValidationError("Cannot change status of a delivered request.")
        if new_status == "delivered" and request_obj.status != "approved":
            raise serializers.ValidationError("Request must be approved before it can be delivered.")

        # Approval validation
        if new_status == "approved":
            cell = request_obj.cell or request_obj.requested_by.managed_cell
            product = request_obj.product
            qty = Decimal(request_obj.quantity_requested or 0)

            district_inventory = DistrictInventory.objects.filter(
                district=cell.sector.district,
                product=product
            ).first()

            if not district_inventory:
                raise serializers.ValidationError(
                    f"No district inventory found for {cell.sector.district.name} - {product.name}"
                )

            # Compute remaining dynamically
            available_qty = district_inventory.quantity_added - district_inventory.quantity_at_cell
            if qty > available_qty:
                raise serializers.ValidationError(
                    f"Not enough quantity remaining in district inventory for cells "
                    f"(available {available_qty}, requested {qty})."
                )

        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        request_user = self.context['request'].user
        old_status = instance.status
        new_status = validated_data.get('status', old_status)
        comment = validated_data.get('comment', instance.comment)

        instance.comment = comment

        if old_status != 'approved' and new_status == 'approved':
            instance.approved_by = request_user
            self.handle_approval(instance)

        elif new_status == 'delivered' and old_status == 'approved':
            instance.delivery_date = timezone.now()

        instance.status = new_status
        instance.save(update_fields=['status', 'approved_by', 'delivery_date', 'comment'])
        return instance

    def handle_approval(self, resource_request):
        cell = resource_request.cell or resource_request.requested_by.managed_cell
        product = resource_request.product
        qty = Decimal(resource_request.quantity_requested or 0)

        # Lock district inventory row
        district_inventory = DistrictInventory.objects.select_for_update().filter(
            district=cell.sector.district,
            product=product
        ).first()

        if not district_inventory:
            raise ValidationError(
                f"No district inventory found for {cell.sector.district.name} - {product.name}"
            )

        # Compute remaining dynamically
        available_qty = district_inventory.quantity_added - district_inventory.quantity_at_cell
        if qty > available_qty:
            raise ValidationError(
                f"Not enough quantity remaining in district inventory for cells "
                f"(available {available_qty}, requested {qty})."
            )

        # Update district inventory
        district_inventory.quantity_at_cell += qty
        district_inventory.save(update_fields=['quantity_at_cell'])

        # Update or create cell inventory
        cell_inventory, created = CellInventory.objects.select_for_update().get_or_create(
            cell=cell,
            product=product,
            defaults={
                'sector': cell.sector,
                'district': cell.sector.district,
                'quantity_available': 0
            }
        )
        cell_inventory.quantity_available += qty
        cell_inventory.save(update_fields=['quantity_available'])

class CellResourceRequestViewSet(viewsets.ModelViewSet):
    queryset = CellResourceRequest.objects.all()
    serializer_class = CellResourceRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return CellResourceRequestReplySerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        user = self.request.user

        if getattr(user, 'user_level', None) == 'cell_officer':
            # Officer: enforce their managed cell
            cell = getattr(user, 'managed_cell', None)
            if not cell:
                raise serializers.ValidationError(
                    {"cell": "This cell officer is not assigned to any cell."}
                )
            serializer.save(cell=cell)
        else:
            # Citizen or other role: they MUST provide cell in request data
            if not serializer.validated_data.get("cell"):
                raise serializers.ValidationError(
                    {"cell": "You are not a cell officer, so skip this request please."}
                )
            serializer.save()



    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Require comment when approving or rejecting
        if request.data.get('status') in ['approved', 'rejected'] and not request.data.get('comment', '').strip():
            return Response(
                {"detail": "Comment is required when approving or rejecting."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        try:
            serializer.save()
        except ValidationError as e:  # catch the model's full_clean errors
            return Response(
                {"detail": e.message_dict if hasattr(e, "message_dict") else e.messages},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(serializer.data)

