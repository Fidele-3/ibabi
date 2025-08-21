import uuid
from django.db import models
from django.utils import timezone
from users.models.customuser import CustomUser
from users.models.addresses import District, Province, Sector, Cell
from users.models.products import Product, ProductPrice, RecommendedQuantity
from report.models import Land, LivestockLocation
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
    quantity_at_cell = models.DecimalField(max_digits=12, decimal_places=2, default=0)  
    # total allocated to cells
    quantity_remaining_at_cells = models.DecimalField(max_digits=12, decimal_places=2, default=0)  
    # live available in all cells combined
    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} - {self.district.name}"

    @property
    def quantity_remaining(self):
        # District stock not yet allocated to cells
        return self.quantity_added - (self.quantity_at_cell or Decimal(0))





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

class FarmerInventory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="farmer_inventories")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    quantity_added = models.PositiveBigIntegerField(default=0, help_text="Total quantity added from delivered resource requests")
    quantity_allocated = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # for future allocations
    quantity_deducted = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # track used/deducted stock
    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.farmer.full_names} - {self.product.name}"

    @property
    def quantity_remaining(self):
        return float(self.quantity_added) - float(self.quantity_allocated or 0) - float(self.quantity_deducted or 0)
    
    def deduct(self, amount):
        if amount > self.quantity_remaining:
            raise ValueError("Cannot deduct more than the remaining quantity.")
        self.quantity_deducted += amount
        self.save()
        return self


from django.db.models import Sum, F
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
        # Validation rules enforcing requested limits
        lands = self.cell.land_set.filter(owner__isnull=False)
        total_hectares = sum([land.size_hectares for land in lands if land.size_hectares])
        requested_qty = self.quantity_requested or Decimal(0)

        recommended = RecommendedQuantity.objects.filter(
            product=self.product,
            crop_name=self.product.name
        ).first()

        planned_crop = getattr(self.cell, 'planned_crop', None)

        recommended_amount = Decimal(0)
        if recommended and total_hectares:
            recommended_amount = Decimal(total_hectares) * recommended.quantity_per_hectare

        district_inventory = DistrictInventory.objects.filter(
            district=self.cell.sector.district,
            product=self.product
        ).first()
        district_qty = Decimal(district_inventory.quantity_remaining) if district_inventory else Decimal(0)

        if planned_crop and planned_crop == self.product:
            max_allowed = recommended_amount * Decimal('1.5')
            if requested_qty > max_allowed:
                raise ValidationError(
                    f"Request exceeds 150% of recommended amount ({max_allowed}) for planned crop."
                )
        elif recommended:
            max_allowed = recommended_amount * Decimal('0.3')
            if requested_qty > max_allowed:
                raise ValidationError(
                    f"Request exceeds 30% of recommended amount ({max_allowed}) for unplanned recommended crop."
                )
        else:
            max_allowed = district_qty * Decimal('0.05')
            if requested_qty > max_allowed:
                raise ValidationError(
                    f"Request exceeds 5% of district inventory ({max_allowed}) for non-recommended product."
                )

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        previous_status = None
        if not is_new:
            previous_status = CellResourceRequest.objects.get(pk=self.pk).status

        self.full_clean()
        super().save(*args, **kwargs)

        # Only trigger updates when status changes to "approved"
        if self.status == "approved" and previous_status != "approved":
            qty = self.quantity_requested

            # Update or create CellInventory
            cell_inventory, _ = CellInventory.objects.get_or_create(
                cell=self.cell,
                sector=self.cell.sector,
                district=self.cell.sector.district,
                product=self.product,
                defaults={'quantity_available': 0}
            )
            cell_inventory.quantity_available += qty
            cell_inventory.save(update_fields=['quantity_available'])

            # Aggregate total remaining in district inventory
            district_inventory_qs = DistrictInventory.objects.filter(
                district=self.cell.sector.district,
                product=self.product
            )

            total_remaining = district_inventory_qs.aggregate(
                total_remaining=Sum(F('quantity_added') - F('quantity_at_cell'))
            )['total_remaining'] or 0

            if qty > total_remaining:
                raise ValidationError(
                    f"Not enough quantity in district inventory (available {total_remaining}, requested {qty})"
                )

            # Distribute the requested quantity to district inventory rows proportionally
            remaining_qty = qty
            for di in district_inventory_qs.order_by('id'):
                available = (di.quantity_added - di.quantity_at_cell)
                if available <= 0:
                    continue

                allocate = min(available, remaining_qty)
                di.quantity_at_cell += allocate
                if not hasattr(di, 'quantity_remaining_at_cells'):
                    di.quantity_remaining_at_cells = 0
                di.quantity_remaining_at_cells += allocate
                di.save(update_fields=['quantity_at_cell', 'quantity_remaining_at_cells'])

                remaining_qty -= allocate
                if remaining_qty <= 0:
                    break

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
    land = models.ForeignKey(Land, on_delete=models.CASCADE, related_name="resource_requests", null=True, blank=True)
    livestock = models.ForeignKey(LivestockLocation, on_delete=models.CASCADE, related_name="resource_requests", null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    quantity_requested = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    request_date = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_requests")
    delivery_date = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True, null=True)

    def clean(self):
        # Must have either land or livestock
        if not self.land and not self.livestock:
            raise ValidationError("Resource request must be tied to either a land or a livestock.")

        # Crop-specific logic if land is set
        if self.land:
            if not self.product:
                planned_crop = getattr(self.land.cell, "planned_crop", None)
                if planned_crop:
                    self.product = planned_crop
                else:
                    raise ValidationError("No product specified and no planned crop found for the cell.")

            now = timezone.now()
            current_season = self.land.cell.get_current_season()
            current_year = self.land.cell.get_current_season_year()

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

        # Livestock requests do not auto-fill; user must provide product and quantity
        if self.livestock and not self.product:
            raise ValidationError("Product must be specified for livestock requests.")

    def save(self, *args, **kwargs):
        self.clean()  # enforce clean before saving

        # Crop logic for auto-fill price and quantity
        if self.land:
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

        # Calculate total price if possible
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
        target = self.land or self.livestock
        return f"{self.product.name} request by {self.farmer.email} ({self.status}) on {target}"

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
