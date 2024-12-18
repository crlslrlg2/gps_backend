# notifications.py

from exponent_server_sdk import PushClient, PushMessage, PushServerError
from requests.exceptions import ConnectionError, HTTPError
from datetime import datetime
import pytz

def send_expo_notification(token, title, message, timestamp, user_timezone="UTC"):
    # Ensure the token is correctly formatted
    if not token.startswith("ExponentPushToken"):
        raise ValueError("Invalid push token")

    # Convert the Unix timestamp to UTC datetime
    utc_time = datetime.utcfromtimestamp(timestamp)
    user_tz = pytz.timezone(user_timezone)
    local_time = utc_time.astimezone(user_tz)
    formatted_time = local_time.strftime('%H:%M %p')

    # Update the message body to include the local timestamp
    updated_message = f"{message} at {formatted_time}"

    try:
        # Send the notification with the updated message
        response = PushClient().publish(
            PushMessage(to=token, title=title, body=updated_message, data={"timestamp": timestamp})
        )
        response.validate_response()
    except (PushServerError, ConnectionError, HTTPError) as exc:
        print(f"Notification error: {exc}")
