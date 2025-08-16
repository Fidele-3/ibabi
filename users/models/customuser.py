import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from ..managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin):

    USER_LEVEL_CHOICES = [
        ("super_admin", "Super Admin"),
        ("district_officer", "District Executive Officer"),
        ("sector_officer", "Sector Executive Officer"),
        ("cell_officer", "Cell Executive Officer"),
        ("technician", "Technician"),
        ("seller", "Seller"),
        ("buyer", "Buyer"),
        ("citizen", "Citizen"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, blank=False, null=False)
    full_names = models.CharField(max_length=151, blank=False)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    user_level = models.CharField(max_length=20, choices=USER_LEVEL_CHOICES, default="citizen")

    # National ID mandatory and unique for all users
    national_id = models.CharField(max_length=17, unique=True, blank=False, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_names', 'national_id']

    def __str__(self):
        return f"{self.full_names} ({self.email})"

    def get_full_name(self):
        return self.full_names

    @property
    def is_super_admin(self):
        return self.user_level == "super_admin"

    @property
    def is_district_officer(self):
        return self.user_level == "district_officer"

    @property
    def is_sector_officer(self):
        return self.user_level == "sector_officer"

    @property
    def is_cell_officer(self):
        return self.user_level == "cell_officer"

    @property
    def is_seller(self):
        return self.user_level == "seller"

    @property
    def is_buyer(self):
        return self.user_level == "buyer"

    @property
    def is_citizen(self):
        return self.user_level == "citizen"

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ['full_names']
