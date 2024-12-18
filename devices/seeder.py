import requests
from django.http import JsonResponse
from .models import *
from django.conf import settings


# Set the URL and headers
url = "https://flespi.io/gw/devices/all"
url_telementry = "https://flespi.io/gw/devices/all/telemetry/all"
headers = {"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}

def get_devices(request):
    try:
        # Send GET request with headers
        response = requests.get(url, headers=headers)
        response_url_telementry = requests.get(url_telementry, headers=headers)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            flespi_devices = response.json().get('result', [])
            flespi_devices_telementrys = response_url_telementry.json().get('result', [])
            flespi_device_ids = {device['id']: device for device in flespi_devices}
            existing_device_ids = set(Device.objects.values_list('device_id', flat=True))
            
            # Delete devices not in the Flespi response
            Device.objects.exclude(device_id__in=flespi_device_ids.keys()).delete()

            for flespi_device,flespi_devices_telementry in zip(flespi_devices,flespi_devices_telementrys):
                print(f"Processing",flespi_device.keys())
                device_id = flespi_device['id']
                device_type_id = flespi_device['device_type_id']
                ident = flespi_device['configuration']['ident']
                name = flespi_device['name']
                vin_number = None
                if flespi_devices_telementry.get('telemetry'):
                    vin_number = flespi_devices_telementry['telemetry'].get('vehicle.vin', {}).get('value')
                

                if device_id in existing_device_ids:
                    # Update existing device
                    device = Device.objects.get(device_id=device_id)
                    user_car_device = UserCarsWithDevice.objects.filter(device=device).first()
                    if user_car_device and user_car_device.car and vin_number:
                        user_car_device.car.vinNumber = vin_number  
                        user_car_device.car.save()
                        print(f"Updated VIN for Car ID {user_car_device.car.id}")
                    if device.name != name or device.device_type_id != device_type_id or device.ident != ident:
                        device.name = name
                        device.device_type_id = device_type_id
                        device.ident = ident
                        device.save()
                        print(f"Updated device ID {device_id}")
                else:
                    # Create new device
                    device = Device(
                        device_id=device_id,
                        device_type_id=device_type_id,
                        ident=ident,
                        status="unselected",  # default status
                        name=name
                    )
                    device.save()
                    print(f"Created device ID {device_id}")

        else:
            # Print error message
            print("Request failed with status code:", response.status_code)
    except requests.RequestException as e:
        # Print error message
        print("Error:", e)
    
    return JsonResponse({"message": "Devices processed successfully"})
