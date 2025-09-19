# executives/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models import Avg
from django.core.exceptions import ObjectDoesNotExist
from .models import Executives
from users.models import UserBlock
from .serializers import ExecutivesSerializer


class ExecutivesListConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.group_name = f'executives_list_{self.user_id}'
        
        # Join the group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial data when connected
        await self.send_executives_list()

    async def disconnect(self, close_code):
        # Leave the group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'get_executives':
                await self.send_executives_list()
            elif action == 'refresh':
                await self.send_executives_list()
            else:
                await self.send(text_data=json.dumps({
                    'error': 'Invalid action. Use "get_executives" or "refresh"'
                }))
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON format'
            }))

    @database_sync_to_async
    def get_executives_data(self):
        try:
            # Get blocked executives for this user
            blocked_executives = UserBlock.objects.filter(
                user_id=self.user_id, 
                is_blocked=True
            ).values_list('executive_id', flat=True)

            # Get executives queryset (same logic as your view)
            queryset = Executives.objects.filter(
                is_suspended=False,
                is_banned=False
            ).exclude(
                id__in=blocked_executives 
            ).annotate(
                average_rating=Avg('call_ratings__stars')  
            ).order_by(
                '-online', 
                '-average_rating'
            )

            # Serialize the data
            serializer = ExecutivesSerializer(
                queryset, 
                many=True,
                context={
                    'user_id': self.user_id,
                    'request': None  # WebSocket doesn't have request object
                }
            )
            
            return serializer.data
            
        except Exception as e:
            return {'error': str(e)}

    async def send_executives_list(self):
        executives_data = await self.get_executives_data()
        
        if isinstance(executives_data, dict) and 'error' in executives_data:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': executives_data['error']
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'executives_list',
                'data': executives_data,
                'user_id': self.user_id
            }))

    # Handle group messages (for real-time updates)
    async def executives_update(self, event):
        """Handle executives update from group"""
        await self.send_executives_list()

    async def executive_status_change(self, event):
        """Handle individual executive status changes"""
        await self.send_executives_list()