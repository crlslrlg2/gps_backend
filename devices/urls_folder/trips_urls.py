from django.urls import path
from devices.views import *
urlpatterns = [
    path('trips/<deviceID>/month/<month>',TripsView.as_view()),
    path('trips/<deviceID>/day/<day>',TripsView.as_view())
]