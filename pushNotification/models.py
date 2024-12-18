from django.db import models
from auth_app.models import *
# Create your models here. 
class FCMToken(models.Model):
    user = models.ForeignKey(UserCustomModel, on_delete=models.CASCADE, related_name='fcm_tokens')
    token = models.CharField(max_length=255)
    timezone = models.CharField(max_length=250, default='America/Los_Angeles')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.token}"