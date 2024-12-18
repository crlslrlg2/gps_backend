from django.urls import path
from .views import *

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
urlpatterns = [
  path('refreshToken/', TokenRefreshView.as_view(), name='token_refresh'),
  path('signup/', SignUpView.as_view(), name='signup'),
  path('login/', LoginView.as_view(), name='login'),
  path('usersList/', UserView.as_view(), name='userList'),
  path('devicesList/', DevicesListView.as_view(), name='DevicesList'),
  path('uploadDevicesBatch/', DeviceBatchUploadView.as_view(), name='device-batch-upload'),
  path('batches/', BatchListView.as_view(), name='batch-list'),
  path('batches/<batch_id>/', BatchListView.as_view()),
  path('batches/<batch_id>/devices/', DevicesInBatchDetailView.as_view(), name='batch-detail'),
  path('batchAssignment/', BatchAssignmentView.as_view(), name='batch-assignment'),
   path('vehicle-device-create/', VehicleAndDeviceCreateAPIView.as_view(), name='vehicle-device-create'),
]