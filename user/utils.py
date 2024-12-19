from django.conf import settings
import requests
import time
import random
from agora_token_builder import RtcTokenBuilder

def send_otp_2factor(mobile_number, otp):
    api_key = settings.TWO_FACTOR_API_KEY
    url = f"https://2factor.in/API/V1/{api_key}/SMS/{mobile_number}/{otp}"

    response = requests.get(url)
    data = response.json()

    if data.get('Status') == 'Success':
        return True
    else:
        raise Exception(f"Failed to send OTP: {data.get('Details')}")


import time
from agora_token_builder import RtcTokenBuilder

AGORA_APP_ID = '9626e8b5f847e6961cb9a996e1ae93'
AGORA_APP_CERTIFICATE = 'ab41eb854807425faa1b44481ff97fe3'
AGORA_TTL = 3600 

def generate_agora_token(channel_name, uid, role="publisher"):
    current_timestamp = int(time.time())
    privilege_expired_ts = current_timestamp + AGORA_TTL

    if role == "publisher":
        rtc_role = 1
    else:
        rtc_role = 2  

    token = RtcTokenBuilder.buildTokenWithUid(
        AGORA_APP_ID,
        AGORA_APP_CERTIFICATE,
        channel_name,
        uid,
        rtc_role,
        privilege_expired_ts,
    )
    return token


