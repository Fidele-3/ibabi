import uuid
from django.db import models
from django.utils import timezone
from users.models.customuser import CustomUser
from users.models.addresses import District, Province, Sector, Cell
from users.models.products import Product, ProductPrice, RecommendedQuantity
from report.models import Land  
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
from django.db import models

class SeasonalCropPlan(models.Model):
    SEASON_CHOICES = [
        ("A", "Season A"),
        ("B", "Season B"),
        ("C", "Season C"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cell = models.ForeignKey(Cell, on_delete=models.CASCADE, related_name="seasonal_crops")
    season = models.CharField(max_length=1, choices=SEASON_CHOICES)
    year = models.PositiveIntegerField(default=timezone.now().year)
    crop = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="seasonal_plans")
    set_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="set_seasonal_crops")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cell", "season", "year")
        ordering = ["-year", "season"]

    def __str__(self):
        return f"{self.get_season_display()} {self.year} - {self.crop.name} ({self.cell.name})"


class DistrictInventory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="inventories")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    
    quantity_added = models.PositiveBigIntegerField(default=0, help_text="Total quantity added to this district inventory")
    quantity_at_cell = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # sum of stock currently allocated to cells
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} - {self.district.name}"

    @property
    def quantity_remaining(self):
        # Remaining = total added - quantity currently allocated to cells
        return self.quantity_added - float(self.quantity_at_cell or 0)





from decimal import Decimal

class CellInventory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cell = models.ForeignKey(Cell, on_delete=models.CASCADE, related_name='inventories')
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name='cell_inventories')
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='cell_inventories')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_available = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} - {self.cell.name} (Sector: {self.sector.name}, District: {self.district.name})"

    def calculate_quantity_available(self):
        """
        Calculate quantity_available based on:
        - Total hectares of registered farmers' lands in this cell
        - Recommended quantity per hectare for the product
        - If product matches planned crop in cell, use recommended quantity, else zero
        """
        lands = self.cell.land_set.filter(owner__isnull=False)
        total_hectares = sum([land.size_hectares for land in lands if land.size_hectares])

        recommended = RecommendedQuantity.objects.filter(
            product=self.product,
            crop_name=self.product.name
        ).first()

        if not recommended or total_hectares == 0:
            return Decimal('0.00')

        planned_crop = getattr(self.cell, 'planned_crop', None)
        if planned_crop and planned_crop == self.product:
            return Decimal(total_hectares) * recommended.quantity_per_hectare

        return Decimal('0.00')

    def save(self, *args, recalc_quantity=False, **kwargs):
        """
        Save method updated to only recalculate quantity_available when
        recalc_quantity=True is passed. Otherwise, quantity_available remains as is.
        """
        if recalc_quantity:
            self.quantity_available = self.calculate_quantity_available()

        super().save(*args, **kwargs)


class CellResourceRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("delivered", "Delivered"),
        ("rejected", "Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cell = models.ForeignKey(Cell, on_delete=models.CASCADE, related_name='resource_requests')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_requested = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    request_date = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_cell_requests')
    delivery_date = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True, null=True)

    def clean(self):
        # Validation rules enforcing your requested limits

        # Total hectares of registered farmers' lands in this cell
        lands = self.cell.land_set.filter(owner__isnull=False)

        total_hectares = sum([land.size_hectares for land in lands if land.size_hectares])
        requested_qty = self.quantity_requested or Decimal(0)

        # Recommended quantity for this product
        recommended = RecommendedQuantity.objects.filter(
            product=self.product,
            crop_name=self.product.name
        ).first()

        # Planned crop for this cell
        planned_crop = getattr(self.cell, 'planned_crop', None)

        # Calculate recommended amount for the cell's lands
        recommended_amount = Decimal(0)
        if recommended and total_hectares:
            recommended_amount = Decimal(total_hectares) * recommended.quantity_per_hectare

        # District inventory for this product and cell's district
        district_inventory = DistrictInventory.objects.filter(
            district=self.cell.sector.district,
            product=self.product
        ).first()
        district_qty = Decimal(district_inventory.quantity_remaining) if district_inventory else Decimal(0)


        # Validation logic
        if planned_crop and planned_crop == self.product:
            # Planned crop - allow up to 150% of recommended
            max_allowed = recommended_amount * Decimal('1.5')
            if requested_qty > max_allowed:
                raise ValidationError(
                    f"Request exceeds 150% of recommended amount ({max_allowed}) for planned crop."
                )
        elif recommended:
            # Unplanned but recommended - max 30%
            max_allowed = recommended_amount * Decimal('0.3')
            if requested_qty > max_allowed:
                raise ValidationError(
                    f"Request exceeds 30% of recommended amount ({max_allowed}) for unplanned recommended crop."
                )
        else:
            # Non-recommended - max 5% of district inventory
            max_allowed = district_qty * Decimal('0.05')
            if requested_qty > max_allowed:
                raise ValidationError(
                    f"Request exceeds 5% of district inventory ({max_allowed}) for non-recommended product."
                )

        # Additional validations can be added here as needed

    def save(self, *args, **kwargs):
        self.full_clean()  # Ensure clean() runs before saving
        super().save(*args, **kwargs)


from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone

class ResourceRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("delivered", "Delivered"),
        ("rejected", "Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="resource_requests")
    land = models.ForeignKey(Land, on_delete=models.CASCADE, related_name="resource_requests", default=None)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)  # Now optional
    quantity_requested = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    request_date = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_requests")
    delivery_date = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True, null=True)
    def clean(self):
        """
        Validation logic for duplicate approved requests in same season.
        Also ensures we have a product (either passed or from planned crop).
        """
        # Auto-fill product if missing
        if not self.product:
            planned_crop = getattr(self.land.cell, "planned_crop", None)
            if planned_crop:
                self.product = planned_crop
            else:
                raise ValidationError("No product specified and no planned crop found for the cell.")

        now = timezone.now()
        current_season = self.land.cell.get_current_season()
        current_year = self.land.cell.get_current_season_year()

        # Check for existing approved request for same product, same land, same season/year
        existing_request = ResourceRequest.objects.filter(
            land=self.land,
            product=self.product,
            status="approved",
            land__cell__season=current_season,
            land__cell__season_year=current_year
        ).exclude(id=self.id).first()

        if existing_request:
            raise ValidationError(
                f"A request for {self.product.name} is already approved for this land "
                f"in Season {current_season} {current_year}."
            )

    def save(self, *args, **kwargs):
        """Auto-fill product, price, and recommended quantity if not set."""
        # Auto-fill product if missing
        if not self.product:
            planned_crop = getattr(self.land.cell, "planned_crop", None)
            if planned_crop:
                self.product = planned_crop

        # Ensure we have a product at this point
        if not self.product:
            raise ValidationError("No product specified and no planned crop found for the cell.")

        # Price lookup
        product_price = ProductPrice.objects.filter(product=self.product).first()
        if product_price and not self.price_per_unit:
            self.price_per_unit = product_price.price

        # Quantity lookup from recommendation
        recommended = RecommendedQuantity.objects.filter(
            product=self.product,
            crop_name=self.product.name
        ).first()

        if recommended and self.land.size_hectares and not self.quantity_requested:
            self.quantity_requested = Decimal(self.land.size_hectares) * recommended.quantity_per_hectare

        # Calculate total price
        if self.price_per_unit and self.quantity_requested:
            self.total_price = Decimal(self.price_per_unit) * Decimal(self.quantity_requested)

        super().save(*args, **kwargs)


    @staticmethod
    def get_current_season(date):
        month = date.month
        if month in [9, 10, 11, 12, 1]:
            return "A"
        elif month in [2, 3, 4, 5, 6]:
            return "B"
        else:
            return "C"

    def __str__(self):
        return f"{self.product.name} request by {self.farmer.email} ({self.status})"



class ResourceRequestFeedback(models.Model):
    request = models.OneToOneField(ResourceRequest, on_delete=models.CASCADE, related_name="feedback")
    farmer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    rating = models.IntegerField()  # 1 to 5 stars
    comment = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.request.id} by {self.farmer.email}"

class LandSeasonalAssignment(models.Model):
   
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    land = models.ForeignKey(Land, on_delete=models.CASCADE, related_name="seasonal_assignments")
    seasonal_plan = models.ForeignKey(SeasonalCropPlan, on_delete=models.CASCADE, related_name="land_assignments")
    auto_assigned = models.BooleanField(default=True)  # if the farmer changes crop, set this to False
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("land", "seasonal_plan")

    def __str__(self):
        return f"{self.land.owner} - {self.seasonal_plan.crop.name} ({self.seasonal_plan.get_season_display()} {self.seasonal_plan.year})"
