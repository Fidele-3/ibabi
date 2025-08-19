from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
from report.models import ResourceRequest, FarmerInventory
@receiver(post_save, sender=ResourceRequest)
def update_farmer_inventory(sender, instance, created, **kwargs):
    """
    Automatically update FarmerInventory when a resource request is delivered.
    """
    if instance.status == "delivered":
        # Ensure quantity is valid
        quantity_to_add = Decimal(instance.quantity_requested or 0)
        if quantity_to_add <= 0:
            return  # skip if no quantity

        # Get or create FarmerInventory for this farmer and product
        inventory, created = FarmerInventory.objects.get_or_create(
            farmer=instance.farmer,
            product=instance.product,
            defaults={'quantity_added': 0, 'quantity_allocated': 0, 'quantity_deducted': 0}
        )

        # Aggregate quantity
        inventory.quantity_added += quantity_to_add
        inventory.save()
