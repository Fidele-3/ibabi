# users/models/land.py
import uuid
from django.db import models
from users.models.addresses import Province, District, Sector, Cell, Village
from users.models.customuser import CustomUser
from users.models.products import Product
from django.utils import timezone
class Land(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="lands")
    upi = models.CharField(max_length=50, unique=True)  # Unique Parcel Identifier
    size_hectares = models.DecimalField(max_digits=10, decimal_places=2)
    province = models.ForeignKey(Province, on_delete=models.CASCADE)
    district = models.ForeignKey(District, on_delete=models.CASCADE)
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE)
    cell = models.ForeignKey(Cell, on_delete=models.CASCADE)
    village = models.ForeignKey(Village, on_delete=models.CASCADE)
    longitude = models.FloatField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_crop = models.ForeignKey

    class Meta:
        unique_together = ('upi', 'owner')

    def __str__(self):
        return f"{self.upi} - {self.size_hectares} ha"

# reports/models.py
class HarvestReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="harvest_reports")
    land = models.ForeignKey(Land, on_delete=models.CASCADE, related_name="harvest_reports",  default=None)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.FloatField(help_text="Quantity in kilograms or liters")
    report_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("sold", "Sold"),
            ("available", "Available")
        ],
        default="available",
        help_text="Status of the Harvest report"
    )

    def __str__(self):
        return f"{self.product.name} - {self.quantity} ({self.farmer.username})"

class LivestockLocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="livestock_locations")
    province = models.ForeignKey(Province, on_delete=models.CASCADE)
    district = models.ForeignKey(District, on_delete=models.CASCADE)
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, related_name="product_locations", blank=True)
    upi = models.CharField(max_length=50, unique=True, help_text="Unique Parcel Identifier for livestock location", null=True, blank=True)
    number_of_products = models.PositiveIntegerField(
        default=0,
        help_text="Number of livestock or products"
    )

    cell = models.ForeignKey(Cell, on_delete=models.CASCADE)
    village = models.ForeignKey(Village, on_delete=models.CASCADE)
    longitude = models.FloatField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("sold", "Sold"),
            ("available", "Available")
        ],
        default="available",
        help_text="Status of the livestock location"
    )


    def __str__(self):
        return f"Livestock location for {self.owner.full_names} in {self.village.name}"
class LivestockAnimal(models.Model):
    livestock_location = models.ForeignKey(LivestockLocation, on_delete=models.CASCADE, related_name="livestock_animals")
    animal = models.ForeignKey(Product, on_delete=models.CASCADE)  # Animal type
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("livestock_location", "animal")


class LivestockProduction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="livestock_productions")
    location = models.ForeignKey(LivestockLocation, on_delete=models.CASCADE, related_name="productions", default=None)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.FloatField(help_text="Quantity in liters or kilograms")
    report_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("sold", "Sold"),
            ("available", "Available")
        ],
        default="available",
        help_text="Status of the livestock production"
    )

    def __str__(self):
        return f"{self.product.category} ({self.product.name}) - {self.quantity}"
