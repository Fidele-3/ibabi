# user/models/userprofile.py

from django.db import models
from .customuser import CustomUser
from .addresses import Province, District, Sector, Cell, Village 
class UserProfile(models.Model):
 
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    bio = models.TextField(blank=True, null=True)
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        blank=True,
        null=True
    )
    date_of_birth = models.DateField(blank=True, null=True)
    work = models.CharField(max_length=50, null=True, blank=True)
    work_description = models.TextField(null=True)
    province= models.ForeignKey(Province, on_delete=models.CASCADE, blank=False, null=True)
    district = models.ForeignKey(District, on_delete=models.CASCADE, blank=False, null=True)
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE,blank=False, null=True)
    cell = models.ForeignKey(Cell, on_delete=models.CASCADE,null=True, blank=False)
    village = models.ForeignKey(Village, on_delete=models.CASCADE,blank=False, null=True)
    website = models.URLField(blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        default='profile_pictures/default.jpg',
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.full_names}"

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-created_at']


class Seller(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    assigned_cell = models.ManyToManyField(Cell, blank=True)
    farm_name = models.CharField(max_length=255, blank=True, null=True)
    license_number = models.CharField(max_length=100, blank=True, null=True)

class Buyer(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    assigned_cell = models.ManyToManyField(Cell, blank=True)
    delivery_address = models.TextField(blank=True, null=True)
