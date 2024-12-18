import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .serializer import DeviceNotificationSerializer
from devices.models import Device
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

class NotificationConsumer(AsyncWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.group_name = None  # Initialize group_name to None

    async def connect(self):
        self.user = self.scope['user']
        print("Connected user:", self.user)

        # Close connection if user is anonymous
        if isinstance(self.user, AnonymousUser):
            print("Anonymous user tried to connect.")
            await self.close(code=4001)  # Custom error code for unauthorized connection
            return

        # Join a group specific to this user
        self.group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Accept the WebSocket connection
        await self.accept()

        # Send all devices associated with the user
        await self.send_all_devices()

    async def disconnect(self, close_code):
        # Ensure that group_name is set before attempting to leave the group
        if self.group_name:
            print(f"Disconnected with close code: {close_code}")
            # Leave the group when the WebSocket connection is closed
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def send_all_devices(self):
        """Fetch and send all devices associated with the user."""
        devices = await self.get_user_devices(self.user)  # Fetch devices asynchronously
        serialized_data = await self.serialize_devices(devices)  # Serialize devices asynchronously

        # Send serialized data over WebSocket
        await self.send(text_data=json.dumps({
            'devices': serialized_data
        }))

    @database_sync_to_async
    def get_user_devices(self, user):
        """Fetch all devices associated with the user."""
        return Device.objects.filter(device_selected_by_user__user=user)

    @database_sync_to_async
    def serialize_devices(self, devices):
        """Serialize the devices asynchronously."""
        return DeviceNotificationSerializer(devices, many=True).data

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        data = json.loads(text_data)
        device_id = data.get('device_id')
        action = data.get('action')

        # Handle reset notification count action
        if action == 'reset_notification':
            await self.reset_notification_count(device_id)
            await self.send_all_devices()

    async def notification_message(self, event):
        """Send updated device notifications."""
        await self.send_all_devices()

    async def send_device_update(self, device_id):
        """Send an update for a specific device after an action."""
        device = await self.get_device_by_id(device_id)
        if device:
            serialized_data = await self.serialize_devices([device])
            await self.send(text_data=json.dumps({
                'device_update': serialized_data
            }))

    @database_sync_to_async
    def get_device_by_id(self, device_id):
        """Fetch a specific device by its ID."""
        try:
            return Device.objects.get(device_id=device_id)
        except Device.DoesNotExist:
            print(f"Device with ID {device_id} does not exist.")
            return None

    @database_sync_to_async
    def reset_notification_count(self, device_id):
        """Reset notification count for a specific device."""
        try:
            device = Device.objects.get(device_id=device_id)
            device.notificationCount = 0
            device.save()
        except Device.DoesNotExist:
            print(f"Device with ID {device_id} does not exist.")
