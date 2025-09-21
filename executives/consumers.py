import json
from channels.generic.websocket import AsyncWebsocketConsumer

# Track executive statuses globally
EXECUTIVE_STATUS = {}  # { executive_id: "online"/"offline"/"oncall" }


class UsersConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "users_online"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send(text_data=json.dumps({
            "type": "executive_status_list",
            "data": [
                {"executive_id": exec_id, "status": status}
                for exec_id, status in EXECUTIVE_STATUS.items()
            ]
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Forward user events (call/status) to executives"""
        try:
            data = json.loads(text_data)

            if "executive_id" in data and "user_id" in data:
                # Broadcast to executives
                await self.channel_layer.group_send(
                    "executives_online",
                    {
                        "type": "user_event",
                        "executive_id": str(data["executive_id"]),
                        "user_id": str(data["user_id"]),
                        "call": data.get("call", False),
                        "status": data.get("status")  
                    }
                )
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON"}))

    # Handle user receiving full executive status list
    async def executive_status_list_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "executive_status_list",
            "data": event["data"]
        }))

    # Handle executive -> user event messages
    async def executive_event(self, event):
        await self.send(text_data=json.dumps(event))


class ExecutivesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.executive_id = str(self.scope['url_route']['kwargs']['id'])
        self.users_group_name = "users_online"
        self.executives_group_name = "executives_online"

        # Join executives group
        await self.channel_layer.group_add(self.executives_group_name, self.channel_name)
        await self.accept()

        # Mark executive as online
        EXECUTIVE_STATUS[self.executive_id] = "online"

        # Broadcast updated full list
        await self.broadcast_status_list()

    async def disconnect(self, close_code):
        EXECUTIVE_STATUS[self.executive_id] = "offline"

        # Broadcast updated full list
        await self.broadcast_status_list()

        await self.channel_layer.group_discard(self.executives_group_name, self.channel_name)

    async def receive(self, text_data):
        """Executives send events (call/status) to users"""
        try:
            data = json.loads(text_data)

            if "user_id" in data:
                await self.channel_layer.group_send(
                    self.users_group_name,
                    {
                        "type": "executive_event",
                        "executive_id": self.executive_id,
                        "user_id": str(data["user_id"]),
                        "call": data.get("call", False),
                        "status": data.get("status")
                    }
                )

            if data.get("connect"):
                EXECUTIVE_STATUS[self.executive_id] = "online"

            elif data.get("disconnect"):
                EXECUTIVE_STATUS[self.executive_id] = "offline"

            if "oncall" in data:
                if data["oncall"] is True:
                    EXECUTIVE_STATUS[self.executive_id] = "oncall"
                elif data["oncall"] is False:
                    EXECUTIVE_STATUS[self.executive_id] = "online"

            await self.broadcast_status_list()

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON"}))

    async def user_event(self, event):
        await self.send(text_data=json.dumps(event))

    async def broadcast_status_list(self):
        await self.channel_layer.group_send(
            self.users_group_name,
            {
                "type": "executive_status_list_event",
                "data": [
                    {"executive_id": exec_id, "status": status}
                    for exec_id, status in EXECUTIVE_STATUS.items()
                ]
            }
        )
