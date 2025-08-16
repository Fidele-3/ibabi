from django.db import models
from users.models import CustomUser  

class Province(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return self.name


class District(models.Model):
    name = models.CharField(max_length=100)
    province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name='districts')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

   
    district_officer = models.OneToOneField(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'user_level': 'district_officer'},
        related_name='managed_district'
    )

    def __str__(self):
        return self.name


class Sector(models.Model):
    name = models.CharField(max_length=100)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='sectors')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    sector_officer = models.OneToOneField(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'user_level': 'sector_officer'},
        related_name='managed_sector'
    )

    def __str__(self):
        return self.name


import uuid

from django.utils import timezone

from users.models.products import Product


class Cell(models.Model):
    # Keep your existing integer ID (default primary key)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    name = models.CharField(max_length=100)
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name='cells')

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    hectares = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Total area of the cell in hectares"
    )

    cell_officer = models.OneToOneField(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'user_level': 'cell_officer'},
        related_name='managed_cell'
    )

    # Seasonal Planning Fields
    season = models.CharField(
        max_length=1,
        choices=[('A', 'Season A'), ('B', 'Season B'), ('C', 'Season C')],
        blank=True,
        null=True,
        help_text="Automatically set based on current month"
    )
    season_year = models.PositiveIntegerField(default=timezone.now().year)

    planned_crop = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planned_cells",
        help_text="Crop planned for this season in this cell"
    )

    planned_livestock = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Optional planned livestock type for the season"
    )

    def __str__(self):
        return f"{self.name} - Season {self.season or 'N/A'} {self.season_year}"

    @staticmethod
    def get_current_season(date=None):
        """Determine the season (A, B, C) based on month."""
        if not date:
            date = timezone.now()
        month = date.month
        if month in [9, 10, 11, 12, 1]:
            return "A"
        elif month in [2, 3, 4, 5, 6]:
            return "B"
        else:
            return "C"

    @staticmethod
    def get_current_season_year(date=None):
        """Handle season-year rollover for Season A starting in September."""
        if not date:
            date = timezone.now()
        month = date.month
        year = date.year
        if month == 1:
            return year - 1
        return year

    def save(self, *args, **kwargs):
        """Auto-assign season and year if not already set."""
        if not self.season:
            self.season = self.get_current_season()
        if not self.season_year:
            self.season_year = self.get_current_season_year()
        super().save(*args, **kwargs)


class Village(models.Model):
    name = models.CharField(max_length=100)
    cell = models.ForeignKey(Cell, on_delete=models.CASCADE, related_name='villages')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return self.name
