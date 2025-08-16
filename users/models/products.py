import uuid
from django.db import models
from .addresses import District, Sector 

class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    CATEGORY_CHOICES = [
        ("livestock", "Livestock"),
        ("dairy", "Dairy"),
        ("crops", "Crops"),
        ("fertilizer", "Fertilizer"),
        ("pesticides", "Pesticides"),
        ("seeds", "Seeds"),
        ("tools", "Tools"),
        ("medicines", "Medicines"),
        ("equipment", "Equipment"),
        ("other", "Other"),
    ]

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="other")
    unit = models.CharField(max_length=50, help_text="e.g., kg, liters, pieces")
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.unit})"


class ProductPrice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='prices')
    district = models.ForeignKey(District, on_delete=models.CASCADE, null=True, blank=True)
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, null=True, blank=True)
    cell = models.ForeignKey("users.Cell", on_delete=models.CASCADE, null=True, blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="RWF")

    

    def __str__(self):
        location = self.cell or self.sector or self.district
        return f"{self.product.name} - {location} @ {self.price} {self.currency}"

class RecommendedQuantity(models.Model):
   
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="recommendations")
    crop_name = models.CharField(max_length=100, help_text="Crop for which this recommendation applies")
    quantity_per_hectare = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Quantity needed per hectare"
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('product', 'crop_name')

    def __str__(self):
        return f"{self.product.name} - {self.crop_name}: {self.quantity_per_hectare} {self.product.unit}/ha"