from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from report.models import CellResourceRequest, CellInventory, DistrictInventory
from users.views.views.inventory import CellResourceRequestSerializer
class CellResourceRequestReplySerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('delivered', 'Delivered')]
    )

    class Meta:
        model = CellResourceRequest
        fields = ['id', 'status', 'comment']
        read_only_fields = ['id']

    def validate(self, data):
        request_obj = self.instance
        new_status = data.get('status', request_obj.status)

        if request_obj.status == "approved" and new_status == "pending":
            raise serializers.ValidationError("Cannot revert an approved request back to pending.")

        if request_obj.status == "delivered":
            raise serializers.ValidationError("Cannot change status of a delivered request.")

        if new_status == "delivered" and request_obj.status != "approved":
            raise serializers.ValidationError("Request must be approved before it can be delivered.")

        if new_status == "approved":
            # Check district inventory stock availability only
            cell = request_obj.cell
            product = request_obj.product
            qty = request_obj.quantity_requested

            district_inventory = DistrictInventory.objects.filter(
                district=cell.sector.district,
                product=product
            ).first()

            if not district_inventory:
                raise serializers.ValidationError(
                    f"No district inventory found for {cell.sector.district.name} - {product.name}"
                )

            quantity_remaining = district_inventory.quantity_added - district_inventory.quantity_at_cell
            if qty > quantity_remaining:
                raise serializers.ValidationError(
                    "Not enough quantity remaining in district inventory to approve this request."
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
        instance.save()
        return instance

    def handle_approval(self, resource_request):
        cell = resource_request.cell
        product = resource_request.product
        qty = resource_request.quantity_requested

        district_inventory = DistrictInventory.objects.select_for_update().filter(
            district=cell.sector.district,
            product=product
        ).first()

        if not district_inventory:
            raise serializers.ValidationError(
                f"No district inventory found for {cell.sector.district.name} - {product.name}"
            )

        quantity_remaining = district_inventory.quantity_added - district_inventory.quantity_at_cell
        if qty > quantity_remaining:
            raise serializers.ValidationError(
                "Not enough quantity remaining in district inventory to approve this request."
            )

        # Deduct quantity from district inventory (quantity_at_cell)
        district_inventory.quantity_at_cell += qty
        district_inventory.save()

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
        cell_inventory.save()


class CellResourceRequestViewSet(viewsets.ModelViewSet):
    queryset = CellResourceRequest.objects.all()
    serializer_class = CellResourceRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return CellResourceRequestReplySerializer
        return super().get_serializer_class()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Require comment on approve/reject
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
        serializer.save()
        return Response(serializer.data)
