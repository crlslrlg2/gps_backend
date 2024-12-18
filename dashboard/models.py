from django.db import models
from auth_app.models import UserCustomModel
import uuid
from devices.models import *
class UserCreationLog(models.Model):
    creator = models.ForeignKey(UserCustomModel, on_delete=models.CASCADE, related_name="created_users")
    created_user = models.ForeignKey(UserCustomModel, on_delete=models.CASCADE, related_name="created_by")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.creator.email} created {self.created_user.email} on {self.created_at}"

# Create your models here.
class DeviceBatchUpload(models.Model):
    # Unique identifier for the batch
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # File containing the batch data
    uploaded_file = models.FileField(upload_to='device_batch_uploads/')

    # Unique batch number
    batch_number = models.CharField(max_length=100, unique=True)

    # Status of the batch, indicating if it's assigned or unassigned
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('unassigned', 'Unassigned'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unassigned')

    # Timestamp for when the batch was uploaded
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # User who created the batch
    created_by = models.ForeignKey(UserCustomModel, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': 'safelink'})

    def __str__(self):
        return f"Batch {self.batch_number} - Status: {self.get_status_display()}"
    
    
class DeviceInventory(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    imei = models.CharField(max_length=255, unique=True, null=True)
    sim_card = models.CharField(max_length=255, null=True)
    iccid = models.CharField(max_length=255, null=True)
    serial_number = models.CharField(max_length=255, null=True)
    model = models.CharField(max_length=255, null=True)
    upload = models.BooleanField(default=False, null=True)
    received_date = models.DateTimeField(auto_now_add=True)
    shipped_date = models.DateField(null=True, blank=True)
    batch = models.ForeignKey(DeviceBatchUpload, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=[('monitor', 'monitor'), ('notmonitor', 'notmonitor')], default='notmonitor')
    price=models.FloatField()

    # Adding installation status field with choices
    INSTALLATION_STATUS_CHOICES = [
        ('uninstall', 'Uninstall'),
        ('pending', 'Pending'),
        ('installed', 'Installed'),
    ]
    installation_status = models.CharField(max_length=10, choices=INSTALLATION_STATUS_CHOICES, default='uninstall')
    
    price = models.CharField(max_length=255,null=True, blank=True)

    def __str__(self):
        return f"Device {self.imei}"


class DeviceBatchAssignment(models.Model):
    """
    Represents the assignment of devices to either an agency or a dealer.
    """
    batch = models.ForeignKey(DeviceBatchUpload, on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(UserCustomModel, on_delete=models.CASCADE, related_name='assigned_by_user')
    assigned_to = models.ForeignKey(UserCustomModel, on_delete=models.CASCADE, related_name='assigned_to_user', limit_choices_to={'role__in': ['agency', 'dealer_super_admin','dealer_admin']})
    previous_assignment = models.ForeignKey(UserCustomModel, on_delete=models.CASCADE, related_name='assigned_previous_user', limit_choices_to={'role__in': ['agency', 'dealer_super_admin','dealer_admin']},null=True,blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Device {self.device.imei} assigned to {self.assigned_to.email}"
class DeviceVehicleSale(models.Model):
    seller = models.ForeignKey(UserCustomModel, on_delete=models.CASCADE, related_name="device_sales")
    buyer = models.ForeignKey(UserCustomModel, on_delete=models.CASCADE, related_name="device_purchases")
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="sales")
    vehicle = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="vehicle_sales")
    sale_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.seller.email} sold Device {self.device.imei} with Vehicle {self.vehicle.vinNumber} to {self.buyer.email} on {self.sale_date}"
