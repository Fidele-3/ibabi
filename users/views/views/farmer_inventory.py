from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum
from decimal import Decimal, InvalidOperation
from report.models import FarmerInventory
from users.serializer.farmer_inventory import FarmerInventorySerializer

class FarmerInventoryViewSet(viewsets.ModelViewSet):
    serializer_class = FarmerInventorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Citizens only see their own inventory
        if getattr(user, 'user_level', None) == 'citizen':
            return FarmerInventory.objects.filter(farmer=user)
        # Staff/admin can see all
        return FarmerInventory.objects.all()

    def get_permissions(self):
        """
        Restrict actions: citizens can't create/update/delete.
        Staff/admin have full access.
        """
        user = self.request.user
        if getattr(user, 'user_level', None) == 'citizen':
            self.http_method_names = ['get', 'head', 'options', 'post']  # keep only GET + deduct action
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        user = request.user
        if getattr(user, 'user_level', None) == 'citizen':
            return Response({"error": "You cannot create inventory."}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        user = request.user
        if getattr(user, 'user_level', None) == 'citizen':
            return Response({"error": "You cannot update inventory."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        if getattr(user, 'user_level', None) == 'citizen':
            return Response({"error": "You cannot delete inventory."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def deduct(self, request, pk=None):
        """
        Deduct a quantity from this inventory item.
        Only the owner (farmer) or staff can deduct.
        """
        inventory = self.get_object()
        user = request.user

        # Permission check
        if getattr(user, 'user_level', None) == 'citizen' and inventory.farmer != user:
            return Response(
                {"error": "You do not have permission to modify this inventory."},
                status=status.HTTP_403_FORBIDDEN
            )

        amount = request.data.get('amount')
        try:
            amount = Decimal(str(amount))
        except (TypeError, ValueError, InvalidOperation):
            return Response({"error": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({"error": "Amount must be greater than zero"}, status=status.HTTP_400_BAD_REQUEST)

        if amount > inventory.quantity_remaining:
            return Response({"error": "Cannot deduct more than remaining quantity"}, status=status.HTTP_400_BAD_REQUEST)

        inventory.deduct(amount)
        serializer = self.get_serializer(inventory)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def aggregated(self, request):
        """
        Return aggregated inventory per farmer and product.
        """
        user = request.user
        qs = FarmerInventory.objects.all()

        if getattr(user, 'user_level', None) == 'citizen':
            qs = qs.filter(farmer=user)

        aggregated = qs.values('farmer', 'product') \
                       .annotate(
                           quantity_added=Sum('quantity_added'),
                           quantity_allocated=Sum('quantity_allocated'),
                           quantity_deducted=Sum('quantity_deducted'),
                       )

        results = []
        for item in aggregated:
            remaining = float(item['quantity_added'] or 0) - float(item['quantity_allocated'] or 0) - float(item['quantity_deducted'] or 0)
            results.append({
                'farmer': item['farmer'],
                'product': item['product'],
                'quantity_added': item['quantity_added'],
                'quantity_allocated': item['quantity_allocated'],
                'quantity_deducted': item['quantity_deducted'],
                'quantity_remaining': remaining,
            })
        return Response(results, status=status.HTTP_200_OK)
