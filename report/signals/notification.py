# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from report.models import (
    HarvestReport,
    LivestockProduction,
    ResourceRequest,
    CellResourceRequest,
    FarmerIssue,
    FarmerIssueReply,
    ResourceRequestFeedback,
)
from report.models.notifications import Notifications, Announcement
from users.models.customuser import CustomUser

# -------------------------------
# Helper Functions
# -------------------------------
def create_notification(recipient, title, message, link=None, is_announcement=False):
    if recipient:
        Notifications.objects.create(
            recipient=recipient,
            title=title,  
            message=message,  
            link=link,
            is_announcement=is_announcement
        )

def broadcast_notification(title, message, link=None):
    for user in CustomUser.objects.all():
        create_notification(user, title, message, link)


# -------------------------------
# HARVEST REPORT
# -------------------------------
@receiver(post_save, sender=HarvestReport)
def notify_harvest_report(sender, instance, created, **kwargs):
    farmer = instance.farmer
    status = instance.status
    if created:
        message = f"Your harvest report for {instance.product.name} ({instance.quantity}) on {instance.report_date} has been received."
        create_notification(farmer, "Harvest Report Created", message)
    else:
        message = f"Your harvest report for {instance.product.name} status changed to {status}."
        create_notification(farmer, "Harvest Report Updated", message)


# -------------------------------
# LIVESTOCK PRODUCTION
# -------------------------------
@receiver(post_save, sender=LivestockProduction)
def notify_livestock_production(sender, instance, created, **kwargs):
    farmer = instance.farmer
    status = instance.status
    if created:
        message = f"Your livestock production report for {instance.product.name} ({instance.quantity}) on {instance.report_date} has been received."
        create_notification(farmer, "Livestock Production Created", message)
    else:
        message = f"Your livestock production report for {instance.product.name} status changed to {status}."
        create_notification(farmer, "Livestock Production Updated", message)


# -------------------------------
# RESOURCE REQUEST (Farmer → Cell Inventory)
# -------------------------------
@receiver(post_save, sender=ResourceRequest)
def notify_resource_request(sender, instance, created, **kwargs):
    farmer = instance.farmer
    cell = instance.land.cell
    cell_officer = getattr(cell, 'cell_officer', None)
    status = instance.status
    upi = instance.land.upi

    if created:
        # Notify farmer
        message = f"Your resource request for {instance.product.name} ({instance.quantity_requested}) has been submitted and is pending approval."
        create_notification(farmer, "Resource Request Submitted", message)
        # Notify cell officer
        if cell_officer:
            message = f"Farmer {farmer.get_full_name()} (UPI: {upi}) requested {instance.product.name} ({instance.quantity_requested}) from {cell.name}."
            create_notification(cell_officer, "New Farmer Resource Request", message)
    else:
        # Notify farmer about status change
        message = f"Your resource request for {instance.product.name} has been {status}."
        create_notification(farmer, f"Resource Request {status.title()}", message)
        # Notify cell officer about status change
        if cell_officer:
            message = f"Resource request for {instance.product.name} from farmer {farmer.get_full_name()} (UPI: {upi}) has been {status}."
            create_notification(cell_officer, f"Farmer Resource Request {status.title()}", message)


# -------------------------------
# CELL RESOURCE REQUEST (Officer → District Inventory)
# -------------------------------
@receiver(post_save, sender=CellResourceRequest)
def notify_cell_resource_request(sender, instance, created, **kwargs):
    cell = instance.cell
    sector = getattr(cell, 'sector', None)
    district_officer = getattr(sector.district, 'district_officer', None) if sector else None
    cell_officer = getattr(cell, 'cell_officer', None)
    status = instance.status

    if created:
        # Notify cell officer who requested
        if cell_officer:
            message = f"You requested {instance.product.name} ({instance.quantity_requested}) from district inventory for {cell.name}."
            create_notification(cell_officer, "Cell Resource Request Submitted", message)
        # Notify district officer
        if district_officer:
            message = f"Cell officer {cell_officer.get_full_name()} requested {instance.product.name} ({instance.quantity_requested}) for {cell.name}."
            create_notification(district_officer, "New Cell Resource Request", message)
    else:
        # Notify cell officer about status update
        if cell_officer:
            message = f"Your request for {instance.product.name} ({instance.quantity_requested}) has been {status}."
            create_notification(cell_officer, f"Cell Resource Request {status.title()}", message)
        # Notify district officer about status update
        if district_officer:
            message = f"Request for {instance.product.name} from cell {cell.name} has been {status}."
            create_notification(district_officer, f"Cell Resource Request {status.title()}", message)


# -------------------------------
# FARMER ISSUE
# -------------------------------
@receiver(post_save, sender=FarmerIssue)
def notify_farmer_issue(sender, instance, created, **kwargs):
    status = instance.status
    if created:
        message = f"Your issue '{instance.issue_type}' reported on {instance.reported_at} has been submitted successfully."
        create_notification(instance.farmer, "Farmer Issue Submitted", message)

    else:
        message = f"Your issue '{instance.issue_type}' status changed to {status}."
        create_notification(instance.farmer, f"Farmer Issue {status.title()}", message)


# -------------------------------
# FARMER ISSUE REPLY
# -------------------------------
@receiver(post_save, sender=FarmerIssueReply)
def notify_farmer_issue_reply(sender, instance, created, **kwargs):
    if created:
        message = f"You have a new reply to your issue '{instance.issue.issue_type}': {instance.message}"
        create_notification(instance.issue.farmer, "New Reply to Your Issue", message)


# -------------------------------
# RESOURCE REQUEST FEEDBACK
# -------------------------------
@receiver(post_save, sender=ResourceRequestFeedback)
def notify_resource_request_feedback(sender, instance, created, **kwargs):
    if created:
        message = f"Your feedback for resource request {instance.request.id} has been submitted successfully."
        create_notification(instance.farmer, "Resource Request Feedback Submitted", message)


# -------------------------------
# ANNOUNCEMENTS
# -------------------------------
@receiver(post_save, sender=Announcement)
def notify_announcement(sender, instance, created, **kwargs):
    if created:
        full_message = f"{instance.title}\n\n{instance.message}"
        for user in CustomUser.objects.all():
            create_notification(
                recipient=user,
                title="Announcement",
                message=full_message,
                is_announcement=True
            )