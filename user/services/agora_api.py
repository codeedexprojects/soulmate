import requests

class AgoraAPIClient:
    def __init__(self):
        # Initialize Agora client with necessary credentials
        self.app_id = "your-agora-app-id"  # Replace with actual app ID
        self.app_certificate = "your-agora-app-certificate"  # Replace with actual app certificate
        self.base_url = "https://api.agora.io/v1/channels/"  # This may differ, adjust based on Agora's documentation

    def end_channel(self, channel_name):
        # Use Agora's API to terminate the channel
        url = f"{self.base_url}{channel_name}/end"
        headers = {"Authorization": f"Bearer {self.app_certificate}"}
        
        response = requests.post(url, headers=headers)
        
        if response.status_code == 200:
            print(f"Channel {channel_name} has been successfully ended.")
        else:
            print(f"Failed to end channel {channel_name}: {response.status_code} - {response.text}")

def stop_channel_service(channel_name):
    # This function interacts with AgoraAPIClient to stop the channel
    try:
        agora_api = AgoraAPIClient()
        agora_api.end_channel(channel_name)
        print(f"Channel {channel_name} has been ended on Agora.")
    except Exception as e:
        print(f"Error while terminating the channel {channel_name}: {e}")
