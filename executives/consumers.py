import json
from channels.generic.websocket import AsyncWebsocketConsumer

# Track executive statuses globally
EXECUTIVE_STATUS = {}  # { executive_id: "online"/"offline" }


class UsersConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "users_online"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send current executive statuses
        await self.send(text_data=json.dumps({
            "type": "executive_status_list",
            "data": EXECUTIVE_STATUS
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Forward user call events to all executives"""
        try:
            data = json.loads(text_data)
            if "call" in data and "executive_id" in data and "user_id" in data:
                # Broadcast to all executives
                await self.channel_layer.group_send(
                    "executives_online",
                    {
                        "type": "user_call",
                        "executive_id": str(data["executive_id"]),
                        "user_id": str(data["user_id"]),
                        "call": data["call"]
                    }
                )
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON"}))

    # Handle executive status updates
    async def executive_status(self, event):
        await self.send(text_data=json.dumps(event))


class ExecutivesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.executive_id = str(self.scope['url_route']['kwargs']['id'])
        self.users_group_name = "users_online"
        self.executives_group_name = "executives_online"

        # Join executives group to receive user call messages
        await self.channel_layer.group_add(self.executives_group_name, self.channel_name)
        await self.accept()

        # Mark this executive as online
        EXECUTIVE_STATUS[self.executive_id] = "online"

        # Broadcast to all users
        await self.channel_layer.group_send(
            self.users_group_name,
            {
                "type": "executive_status",
                "executive_id": self.executive_id,
                "status": "online"
            }
        )

    async def disconnect(self, close_code):
        EXECUTIVE_STATUS[self.executive_id] = "offline"

        await self.channel_layer.group_send(
            self.users_group_name,
            {
                "type": "executive_status",
                "executive_id": self.executive_id,
                "status": "offline"
            }
        )

        await self.channel_layer.group_discard(self.executives_group_name, self.channel_name)

    async def receive(self, text_data):
        """Handle manual connect/disconnect messages from executive"""
        try:
            data = json.loads(text_data)
            if data.get("connect"):
                EXECUTIVE_STATUS[self.executive_id] = "online"
                await self.channel_layer.group_send(
                    self.users_group_name,
                    {
                        "type": "executive_status",
                        "executive_id": self.executive_id,
                        "status": "online"
                    }
                )
            elif data.get("disconnect"):
                EXECUTIVE_STATUS[self.executive_id] = "offline"
                await self.channel_layer.group_send(
                    self.users_group_name,
                    {
                        "type": "executive_status",
                        "executive_id": self.executive_id,
                        "status": "offline"
                    }
                )
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON"}))

    # Receive call events from users
    async def user_call(self, event):
        await self.send(text_data=json.dumps(event))
