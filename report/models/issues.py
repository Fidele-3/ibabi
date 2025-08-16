

import uuid
from django.db import models
from users.models.customuser import CustomUser
from users.models.addresses import Province, District, Sector, Cell, Village

class FarmerIssue(models.Model):
    ISSUE_TYPES = [
        ("pests", "Pests"),
        ("disease", "Disease"),
        ("drought", "Drought"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="issues")
    issue_type = models.CharField(max_length=50, choices=ISSUE_TYPES)
    description = models.TextField()
    photo = models.ImageField(upload_to="issues/photos/", blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    reported_at = models.DateTimeField(auto_now_add=True)

    province = models.ForeignKey(Province, on_delete=models.CASCADE)
    district = models.ForeignKey(District, on_delete=models.CASCADE)
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE)
    cell = models.ForeignKey(Cell, on_delete=models.CASCADE)
    village = models.ForeignKey(Village, on_delete=models.CASCADE)

    status = models.CharField(max_length=50, default="Pending")  

    def __str__(self):
        return f"{self.issue_type} - {self.farmer.full_names}"
    
class FarmerIssueReply(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    issue = models.ForeignKey(FarmerIssue, on_delete=models.CASCADE, related_name='replies')
    responder = models.ForeignKey(CustomUser, on_delete=models.CASCADE)  # admin or agronomist
    message = models.TextField()
    replied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply by {self.responder.full_names} on {self.issue.id}"

