import json
import uuid
import time
import threading
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.db import models
from django.db.models import Avg
from calls.models import AgoraCallHistory, CallRating
from executives.models import Executives
from users.models import User
from users.utils import generate_agora_token


class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            # Get user from middleware (can be None)
            self.user = self.scope.get("user")
            
            print(f"WebSocket: Connection attempt for user {self.user.id if self.user else 'None'}")
            
            # Accept the connection regardless of authentication
            await self.accept()
            
            # Create user-specific groups only if user exists
            self.user_group_name = None
            self.executive_group_name = None
            
            if self.user:
                self.user_group_name = f"user_{self.user.id}"
                await self.channel_layer.group_add(
                    self.user_group_name,
                    self.channel_name
                )
                
                # Check if user is an executive
                executive = await self.get_executive_for_user(self.user)
                if executive:
                    self.executive_group_name = f"executive_{executive.id}"
                    await self.channel_layer.group_add(
                        self.executive_group_name,
                        self.channel_name
                    )
                    print(f"WebSocket: User {self.user.id} is executive {executive.id}")
            
            # Send connection confirmation
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'WebSocket connected successfully!',
                'user_id': self.user.id if self.user else None,
                'executive_id': executive.id if self.user and executive else None,
                'timestamp': timezone.now().isoformat(),
                'status': 'connected'
            }))
            
            print(f"WebSocket: Connection established")
            
        except Exception as e:
            print(f"WebSocket connection error: {e}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        print(f"WebSocket disconnected with code: {close_code}")
        
        # Leave groups
        if hasattr(self, 'user_group_name') and self.user_group_name:
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
        
        if hasattr(self, 'executive_group_name') and self.executive_group_name:
            await self.channel_layer.group_discard(
                self.executive_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            print(f"Received WebSocket message: {data}")
            
            # Handle messages that require user authentication
            if message_type in ['initiate_call', 'call_action', 'create_rating', 'mark_joined']:
                user_id = data.get('user_id')
                if not user_id:
                    await self.send_error("user_id is required for this action")
                    return
                
                # Get user from database
                user = await self.get_user_by_id(user_id)
                if not user:
                    await self.send_error("Invalid user_id")
                    return
                
                # Temporarily set user for this request
                self.current_user = user
            else:
                self.current_user = self.user
            
            # Connection and utility messages
            if message_type == 'ping':
                await self.handle_ping()
                
            elif message_type == 'test_connection':
                await self.handle_test_connection()
                
            elif message_type == 'get_user_info':
                await self.handle_get_user_info(data)
                
            # Call management messages
            elif message_type == 'initiate_call':
                await self.handle_initiate_call(data)
                
            elif message_type == 'call_action':
                await self.handle_call_action(data)
                
            elif message_type == 'get_call_by_channel':
                await self.handle_get_call_by_channel(data)
                
            elif message_type == 'mark_joined':
                await self.handle_mark_joined(data)
                
            # Rating messages
            elif message_type == 'create_rating':
                await self.handle_create_rating(data)
                
            elif message_type == 'get_executive_ratings':
                await self.handle_get_executive_ratings(data)
                
            elif message_type == 'get_user_ratings':
                await self.handle_get_user_ratings(data)
                
            elif message_type == 'get_executive_average_rating':
                await self.handle_get_executive_average_rating(data)
                
            elif message_type == 'get_all_ratings':
                await self.handle_get_all_ratings()
                
            # Heartbeat
            elif message_type == 'heartbeat':
                await self.handle_heartbeat(data)
                
            else:
                await self.send_error(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            print(f"Error processing WebSocket message: {e}")
            await self.send_error(f"Error processing message: {str(e)}")

    # Utility handlers
    async def handle_ping(self):
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': timezone.now().isoformat(),
            'message': 'WebSocket is working perfectly!',
            'user_id': self.current_user.id if self.current_user else None
        }))

    async def handle_test_connection(self):
        await self.send(text_data=json.dumps({
            'type': 'connection_test_response',
            'timestamp': timezone.now().isoformat(),
            'message': 'Connection test successful',
            'server_status': 'running',
            'websocket_status': 'connected',
            'user_authenticated': self.current_user is not None,
            'user_id': self.current_user.id if self.current_user else None
        }))

    async def handle_get_user_info(self, data):
        user_id = data.get('user_id')
        if not user_id:
            await self.send_error("user_id is required")
            return
            
        user = await self.get_user_by_id(user_id)
        if not user:
            await self.send_error("User not found")
            return
            
        executive = await self.get_executive_for_user(user)
        await self.send(text_data=json.dumps({
            'type': 'user_info',
            'user_id': user.id,
            'mobile_number': getattr(user, 'mobile_number', 'N/A'),
            'is_executive': executive is not None,
            'executive_id': executive.id if executive else None,
            'timestamp': timezone.now().isoformat()
        }))

    # Call management handlers
    async def handle_initiate_call(self, data):
        """Initiate a new call"""
        if not self.current_user:
            await self.send_error("User authentication required")
            return
            
        executive_id = data.get('executive_id')
        channel_name = data.get('channel_name')
        caller_uid = data.get('caller_uid')

        if not all([executive_id, caller_uid]):
            await self.send_error("executive_id and caller_uid are required")
            return

        # Generate channel name if not provided
        if not channel_name:
            channel_name = f"bestie_{uuid.uuid4().hex[:8]}_{int(time.time())}"

        try:
            executive = await self.get_executive_by_id(executive_id)
            if not executive:
                await self.send_error("Executive not found")
                return

            # Validate executive availability
            validation_error = await self.validate_executive_availability(executive)
            if validation_error:
                await self.send_error(validation_error)
                return

            # Check user balance (if applicable)
            user_balance_check = await self.check_user_balance(self.current_user)
            if user_balance_check:
                await self.send_error(user_balance_check)
                return

            # Mark executive as on call
            await self.mark_executive_on_call(executive, True)

            # Generate tokens
            caller_token = await self.generate_token(channel_name, caller_uid)
            callee_uid = caller_uid + 1000  # Simple UID generation
            executive_token = await self.generate_token(channel_name, callee_uid)

            # Create call history
            call_history = await self.create_call_history({
                'user': self.current_user,
                'executive': executive,
                'channel_name': channel_name,
                'uid': caller_uid,
                'token': caller_token,
                'executive_token': executive_token,
                'status': 'pending',
                'start_time': timezone.now(),
                'executive_joined': False
            })

            # Send incoming call notification to executive
            await self.channel_layer.group_send(
                f"executive_{executive_id}",
                {
                    "type": "incoming_call_notification",
                    "call_id": call_history.id,
                    "channel_name": channel_name,
                    "caller_name": getattr(self.current_user, "name", "Unknown"),
                    "caller_uid": caller_uid,
                    "executive_token": executive_token,
                    "callee_uid": callee_uid,
                    "timestamp": timezone.now().isoformat()
                }
            )

            # Schedule missed call check
            await self.schedule_missed_call_check(call_history.id, executive.id)

            # Send success response
            await self.send(text_data=json.dumps({
                'type': 'call_initiated',
                'success': True,
                'call_data': {
                    'id': call_history.id,
                    'executive_id': executive_id,
                    'channel_name': channel_name,
                    'caller_uid': caller_uid,
                    'token': caller_token,
                    'status': 'pending'
                },
                'message': 'Call initiated successfully',
                'timestamp': timezone.now().isoformat()
            }))

        except Exception as e:
            await self.send_error(f"Error initiating call: {str(e)}")

    async def handle_call_action(self, data):
        """Handle call actions like accept, reject, end, etc."""
        if not self.current_user:
            await self.send_error("User authentication required")
            return
            
        action = data.get('action')
        call_id = data.get('call_id')
        
        if not call_id:
            await self.send_error("Call ID is required")
            return
            
        try:
            call = await self.get_call_by_id(call_id)
            if not call:
                await self.send_error("Call not found")
                return
                
        except Exception as e:
            await self.send_error(f"Error finding call: {str(e)}")
            return

        if action == 'accept_call':
            await self.accept_call(call)
        elif action == 'reject_call':
            await self.reject_call(call)
        elif action == 'end_call':
            await self.end_call(call)
        elif action == 'cancel_call':
            await self.cancel_call(call)
        elif action == 'join_call':
            await self.join_call(call)
        else:
            await self.send_error(f"Unknown action: {action}")

    # ... (rest of the methods remain the same as in your original code)
    
    async def accept_call(self, call):
        """Executive accepts the call"""
        executive = await self.get_executive_for_user(self.current_user)
        if not executive or call.executive.id != executive.id:
            await self.send_error("You don't have permission to accept this call")
            return
            
        if call.status != 'pending':
            await self.send_error(f"Call is not in pending state. Current status: {call.status}")
            return
            
        await database_sync_to_async(self.update_call_status)(call, 'ringing')
        
        # Notify caller
        await self.channel_layer.group_send(
            f"user_{call.user.id}",
            {
                'type': 'call_accepted_event',
                'call_id': call.id,
                'executive_token': getattr(call, 'executive_token', ''),
                'callee_uid': getattr(call, 'callee_uid', None)
            }
        )
        
        await self.send(text_data=json.dumps({
            'type': 'action_success',
            'action': 'accept_call',
            'call_id': call.id,
            'status': 'ringing',
            'message': 'Call accepted successfully',
            'timestamp': timezone.now().isoformat()
        }))

    # Database operations
    @database_sync_to_async
    def get_executive_for_user(self, user):
        """Get executive profile for the given user"""
        if not user:
            return None
        try:
            return Executives.objects.filter(user=user).first()
        except Exception:
            return None

    @database_sync_to_async
    def get_executive_by_id(self, executive_id):
        """Get executive by ID"""
        try:
            return Executives.objects.get(id=executive_id)
        except Executives.DoesNotExist:
            return None

    @database_sync_to_async
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def get_call_by_id(self, call_id):
        """Get call by ID"""
        try:
            return AgoraCallHistory.objects.get(id=call_id)
        except AgoraCallHistory.DoesNotExist:
            return None

    @database_sync_to_async
    def validate_executive_availability(self, executive):
        """Validate executive availability"""
        if not executive.online:
            return "Executive is offline"
        if executive.is_banned:
            return "Executive is banned"
        if executive.on_call:
            return "Executive is on another call"
        return None

    @database_sync_to_async
    def check_user_balance(self, user):
        """Check if user has sufficient balance"""
        if hasattr(user, 'coin_balance') and user.coin_balance < 180:
            return "Insufficient balance. You need at least 180 coins to start a call."
        if hasattr(user, 'is_suspended') and user.is_suspended:
            return "You can't make call, Account is suspended."
        return None

    @database_sync_to_async
    def mark_executive_on_call(self, executive, on_call=True):
        """Mark executive as on call or available"""
        executive.on_call = on_call
        executive.save(update_fields=['on_call'])

    @database_sync_to_async
    def generate_token(self, channel_name, uid):
        """Generate Agora token"""
        return generate_agora_token(channel_name, uid)

    @database_sync_to_async
    def create_call_history(self, call_data):
        """Create call history record"""
        return AgoraCallHistory.objects.create(**call_data)

    @database_sync_to_async
    def schedule_missed_call_check(self, call_id, executive_id):
        """Schedule missed call check - in production use Celery"""
        def mark_as_missed():
            time.sleep(30)
            try:
                call = AgoraCallHistory.objects.filter(
                    id=call_id, 
                    status='pending'
                ).first()
                if call:
                    call.status = 'missed'
                    call.save()
                    # Clear executive on_call status
                    Executives.objects.filter(id=executive_id).update(on_call=False)
            except Exception as e:
                print(f"Error in missed call check: {e}")

        threading.Thread(target=mark_as_missed).start()

    @database_sync_to_async
    def update_call_status(self, call, status):
        call.status = status
        call.save(update_fields=['status'])

    async def send_error(self, message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
            'timestamp': timezone.now().isoformat(),
            'status': 'error'
        }))

    # WebSocket event handlers for incoming messages from other consumers
    async def incoming_call_notification(self, event):
        """Handle incoming call notification"""
        await self.send(text_data=json.dumps({
            'type': 'incoming_call',
            'call_id': event['call_id'],
            'channel_name': event['channel_name'],
            'caller_name': event['caller_name'],
            'caller_uid': event['caller_uid'],
            'executive_token': event['executive_token'],
            'callee_uid': event['callee_uid'],
            'timestamp': event['timestamp']
        }))

    async def call_accepted_event(self, event):
        """Handle call accepted event"""
        await self.send(text_data=json.dumps({
            'type': 'call_accepted',
            **event
        }))