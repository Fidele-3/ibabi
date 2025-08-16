import uuid
from django.db import models
from users.models.addresses import Sector, Cell, Village
from users.models.customuser import CustomUser

class ibabiSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    date = models.DateField()
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name='ibabi_sessions')
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sector_created_sessions',
        help_text="Sector admin who initiated the ibabi date"
    )
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        unique_together = ('date', 'sector')
        ordering = ['-date']

    def __str__(self):
        return f"{self.sector.name} - {self.date}"


class CellibabiSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sector_session = models.ForeignKey(ibabiSession, on_delete=models.CASCADE, related_name='cell_sessions')
    cell = models.ForeignKey(Cell, on_delete=models.CASCADE, related_name='cell_ibabi_sessions')
    village = models.ForeignKey(Village, on_delete=models.SET_NULL, null=True, blank=True)

    tools_needed = models.TextField(blank=True, null=True)
    fines_policy = models.PositiveIntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    other_details = models.TextField(blank=True, null=True)

    updated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('sector_session', 'cell')
