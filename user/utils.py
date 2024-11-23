from django.conf import settings
import requests


def send_otp_2factor(mobile_number, otp):
    api_key = settings.TWO_FACTOR_API_KEY
    url = f"https://2factor.in/API/V1/{api_key}/SMS/{mobile_number}/{otp}"

    response = requests.get(url)
    data = response.json()

    if data.get('Status') == 'Success':
        return True
    else:
        raise Exception(f"Failed to send OTP: {data.get('Details')}")
