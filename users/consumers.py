# users/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Avg
from .models import User, Favourite, UserBlock
from executives.models import Executives
from .serializers import FavouriteSerializer, UserMaxCallTimeSerializer
from executives.serializers import ExecutivesSerializer


class UsersConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            # Accept the connection
            await self.accept()
            
            # Send connection confirmation
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Users WebSocket connected successfully!',
                'timestamp': timezone.now().isoformat(),
                'status': 'connected'
            }))
            
            print(f"Users WebSocket: Connection established")
            
        except Exception as e:
            print(f"Users WebSocket connection error: {e}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        print(f"Users WebSocket disconnected with code: {close_code}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            print(f"Received Users WebSocket message: {data}")
            
            # Connection and utility messages
            if message_type == 'ping':
                await self.handle_ping()
                
            elif message_type == 'test_connection':
                await self.handle_test_connection()
                
            # Favourites management
            elif message_type == 'get_favourites':
                await self.handle_get_favourites(data)
                
            elif message_type == 'add_favourite':
                await self.handle_add_favourite(data)
                
            elif message_type == 'remove_favourite':
                await self.handle_remove_favourite(data)
                
            # User coin balance
            elif message_type == 'get_user_coin_balance':
                await self.handle_get_user_coin_balance(data)
                
            # Executives by user (with blocking logic)
            elif message_type == 'get_executives_by_user':
                await self.handle_get_executives_by_user(data)
                
            # User blocking management
            elif message_type == 'block_executive':
                await self.handle_block_executive(data)
                
            elif message_type == 'unblock_executive':
                await self.handle_unblock_executive(data)
                
            elif message_type == 'get_blocked_executives':
                await self.handle_get_blocked_executives(data)
                
            # User profile management
            elif message_type == 'get_user_profile':
                await self.handle_get_user_profile(data)
                
            elif message_type == 'update_user_profile':
                await self.handle_update_user_profile(data)
                
            else:
                await self.send_error(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            print(f"Error processing Users WebSocket message: {e}")
            await self.send_error(f"Error processing message: {str(e)}")

    # Utility handlers
    async def handle_ping(self):
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': timezone.now().isoformat(),
            'message': 'Users WebSocket is working perfectly!'
        }))

    async def handle_test_connection(self):
        await self.send(text_data=json.dumps({
            'type': 'connection_test_response',
            'timestamp': timezone.now().isoformat(),
            'message': 'Users connection test successful',
            'server_status': 'running',
            'websocket_status': 'connected'
        }))

    # Favourites handlers
    async def handle_get_favourites(self, data):
        """Handle get favourites list - converted from ListFavouritesView"""
        user_id = data.get('user_id')
        if not user_id:
            await self.send_error("user_id is required")
            return
        
        try:
            favourites_data = await self.get_favourites_by_user(user_id)
            await self.send(text_data=json.dumps({
                'type': 'favourites_list',
                'user_id': user_id,
                'data': favourites_data,
                'timestamp': timezone.now().isoformat(),
                'success': True
            }))
        except Exception as e:
            await self.send_error(f"Error fetching favourites: {str(e)}")

    async def handle_add_favourite(self, data):
        """Add executive to favourites"""
        user_id = data.get('user_id')
        executive_id = data.get('executive_id')
        
        if not user_id or not executive_id:
            await self.send_error("user_id and executive_id are required")
            return
        
        try:
            result = await self.add_favourite(user_id, executive_id)
            if result['success']:
                await self.send(text_data=json.dumps({
                    'type': 'favourite_added',
                    'user_id': user_id,
                    'executive_id': executive_id,
                    'message': 'Executive added to favourites',
                    'timestamp': timezone.now().isoformat(),
                    'success': True
                }))
            else:
                await self.send_error(result['message'])
        except Exception as e:
            await self.send_error(f"Error adding favourite: {str(e)}")

    async def handle_remove_favourite(self, data):
        """Remove executive from favourites"""
        user_id = data.get('user_id')
        executive_id = data.get('executive_id')
        
        if not user_id or not executive_id:
            await self.send_error("user_id and executive_id are required")
            return
        
        try:
            result = await self.remove_favourite(user_id, executive_id)
            await self.send(text_data=json.dumps({
                'type': 'favourite_removed',
                'user_id': user_id,
                'executive_id': executive_id,
                'message': result['message'],
                'timestamp': timezone.now().isoformat(),
                'success': result['success']
            }))
        except Exception as e:
            await self.send_error(f"Error removing favourite: {str(e)}")

    # User coin balance handler
    async def handle_get_user_coin_balance(self, data):
        """Handle get user coin balance - converted from UserCoinBalanceView"""
        user_id = data.get('user_id')
        if not user_id:
            await self.send_error("user_id is required")
            return
        
        try:
            user_data = await self.get_user_coin_balance(user_id)
            if not user_data:
                await self.send_error("User not found")
                return
                
            await self.send(text_data=json.dumps({
                'type': 'user_coin_balance',
                'user_id': user_id,
                'data': user_data,
                'timestamp': timezone.now().isoformat(),
                'success': True
            }))
        except Exception as e:
            await self.send_error(f"Error fetching user coin balance: {str(e)}")

    # Executives by user handler
    async def handle_get_executives_by_user(self, data):
        """Handle get executives by user - converted from ListExecutivesByUserView"""
        user_id = data.get('user_id')
        if not user_id:
            await self.send_error("user_id is required")
            return
        
        try:
            executives_data = await self.get_executives_by_user(user_id)
            await self.send(text_data=json.dumps({
                'type': 'executives_by_user',
                'user_id': user_id,
                'data': executives_data,
                'timestamp': timezone.now().isoformat(),
                'success': True
            }))
        except Exception as e:
            await self.send_error(f"Error fetching executives: {str(e)}")

    # User blocking handlers
    async def handle_block_executive(self, data):
        """Block an executive"""
        user_id = data.get('user_id')
        executive_id = data.get('executive_id')
        
        if not user_id or not executive_id:
            await self.send_error("user_id and executive_id are required")
            return
        
        try:
            result = await self.block_executive(user_id, executive_id)
            await self.send(text_data=json.dumps({
                'type': 'executive_blocked',
                'user_id': user_id,
                'executive_id': executive_id,
                'message': result['message'],
                'timestamp': timezone.now().isoformat(),
                'success': result['success']
            }))
        except Exception as e:
            await self.send_error(f"Error blocking executive: {str(e)}")

    async def handle_unblock_executive(self, data):
        """Unblock an executive"""
        user_id = data.get('user_id')
        executive_id = data.get('executive_id')
        
        if not user_id or not executive_id:
            await self.send_error("user_id and executive_id are required")
            return
        
        try:
            result = await self.unblock_executive(user_id, executive_id)
            await self.send(text_data=json.dumps({
                'type': 'executive_unblocked',
                'user_id': user_id,
                'executive_id': executive_id,
                'message': result['message'],
                'timestamp': timezone.now().isoformat(),
                'success': result['success']
            }))
        except Exception as e:
            await self.send_error(f"Error unblocking executive: {str(e)}")

    async def handle_get_blocked_executives(self, data):
        """Get list of blocked executives for user"""
        user_id = data.get('user_id')
        if not user_id:
            await self.send_error("user_id is required")
            return
        
        try:
            blocked_data = await self.get_blocked_executives(user_id)
            await self.send(text_data=json.dumps({
                'type': 'blocked_executives_list',
                'user_id': user_id,
                'data': blocked_data,
                'timestamp': timezone.now().isoformat(),
                'success': True
            }))
        except Exception as e:
            await self.send_error(f"Error fetching blocked executives: {str(e)}")

    # User profile handlers
    async def handle_get_user_profile(self, data):
        """Get user profile"""
        user_id = data.get('user_id')
        if not user_id:
            await self.send_error("user_id is required")
            return
        
        try:
            profile_data = await self.get_user_profile(user_id)
            if not profile_data:
                await self.send_error("User not found")
                return
                
            await self.send(text_data=json.dumps({
                'type': 'user_profile',
                'user_id': user_id,
                'data': profile_data,
                'timestamp': timezone.now().isoformat(),
                'success': True
            }))
        except Exception as e:
            await self.send_error(f"Error fetching user profile: {str(e)}")

    async def handle_update_user_profile(self, data):
        """Update user profile"""
        user_id = data.get('user_id')
        profile_data = data.get('profile_data')
        
        if not user_id or not profile_data:
            await self.send_error("user_id and profile_data are required")
            return
        
        try:
            result = await self.update_user_profile(user_id, profile_data)
            if result['success']:
                await self.send(text_data=json.dumps({
                    'type': 'user_profile_updated',
                    'user_id': user_id,
                    'data': result['data'],
                    'message': 'Profile updated successfully',
                    'timestamp': timezone.now().isoformat(),
                    'success': True
                }))
            else:
                await self.send_error(result['message'])
        except Exception as e:
            await self.send_error(f"Error updating user profile: {str(e)}")

    # Database operations
    @database_sync_to_async
    def get_favourites_by_user(self, user_id):
        """Get favourites for a user"""
        try:
            favourites = Favourite.objects.filter(user_id=user_id)
            serializer = FavouriteSerializer(favourites, many=True)
            return serializer.data
        except Exception as e:
            raise Exception(f"Error fetching favourites: {str(e)}")

    @database_sync_to_async
    def add_favourite(self, user_id, executive_id):
        """Add executive to favourites"""
        try:
            user = User.objects.get(id=user_id)
            executive = Executives.objects.get(id=executive_id)
            
            favourite, created = Favourite.objects.get_or_create(
                user=user,
                executive=executive
            )
            
            if created:
                return {'success': True, 'message': 'Executive added to favourites'}
            else:
                return {'success': False, 'message': 'Executive is already in favourites'}
        except User.DoesNotExist:
            return {'success': False, 'message': 'User not found'}
        except Executives.DoesNotExist:
            return {'success': False, 'message': 'Executive not found'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    @database_sync_to_async
    def remove_favourite(self, user_id, executive_id):
        """Remove executive from favourites"""
        try:
            deleted_count = Favourite.objects.filter(
                user_id=user_id,
                executive_id=executive_id
            ).delete()[0]
            
            if deleted_count > 0:
                return {'success': True, 'message': 'Executive removed from favourites'}
            else:
                return {'success': False, 'message': 'Favourite not found'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    @database_sync_to_async
    def get_user_coin_balance(self, user_id):
        """Get user coin balance"""
        try:
            user = get_object_or_404(User, id=user_id)
            serializer = UserMaxCallTimeSerializer(user)
            return serializer.data
        except Exception:
            return None

    @database_sync_to_async
    def get_executives_by_user(self, user_id):
        """Get executives list filtered by user blocks"""
        try:
            # Get blocked executives for this user
            blocked_executives = UserBlock.objects.filter(
                user_id=user_id, 
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
                    'user_id': user_id,
                    'request': None
                }
            )
            
            return serializer.data
            
        except Exception as e:
            raise Exception(f"Error fetching executives: {str(e)}")

    @database_sync_to_async
    def block_executive(self, user_id, executive_id):
        """Block an executive"""
        try:
            user = User.objects.get(id=user_id)
            executive = Executives.objects.get(id=executive_id)
            
            user_block, created = UserBlock.objects.get_or_create(
                user=user,
                executive=executive,
                defaults={'is_blocked': True}
            )
            
            if not created:
                user_block.is_blocked = True
                user_block.save()
            
            return {'success': True, 'message': 'Executive blocked successfully'}
        except User.DoesNotExist:
            return {'success': False, 'message': 'User not found'}
        except Executives.DoesNotExist:
            return {'success': False, 'message': 'Executive not found'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    @database_sync_to_async
    def unblock_executive(self, user_id, executive_id):
        """Unblock an executive"""
        try:
            updated_count = UserBlock.objects.filter(
                user_id=user_id,
                executive_id=executive_id
            ).update(is_blocked=False)
            
            if updated_count > 0:
                return {'success': True, 'message': 'Executive unblocked successfully'}
            else:
                return {'success': False, 'message': 'Block relationship not found'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    @database_sync_to_async
    def get_blocked_executives(self, user_id):
        """Get blocked executives for user"""
        try:
            blocked_executives = UserBlock.objects.filter(
                user_id=user_id,
                is_blocked=True
            ).select_related('executive')
            
            data = []
            for block in blocked_executives:
                data.append({
                    'executive_id': block.executive.id,
                    'executive_name': block.executive.name,
                    'blocked_at': block.created_at.isoformat() if hasattr(block, 'created_at') else None
                })
            
            return data
        except Exception as e:
            raise Exception(f"Error fetching blocked executives: {str(e)}")

    @database_sync_to_async
    def get_user_profile(self, user_id):
        """Get user profile"""
        try:
            user = User.objects.get(id=user_id)
            # You can create a UserProfileSerializer or return basic data
            return {
                'id': user.id,
                'name': getattr(user, 'name', ''),
                'email': getattr(user, 'email', ''),
                'mobile_number': getattr(user, 'mobile_number', ''),
                'gender': getattr(user, 'gender', ''),
                'coin_balance': getattr(user, 'coin_balance', 0),
                'is_suspended': getattr(user, 'is_suspended', False),
                'created_at': user.date_joined.isoformat() if hasattr(user, 'date_joined') else None
            }
        except User.DoesNotExist:
            return None
        except Exception as e:
            raise Exception(f"Error fetching user profile: {str(e)}")

    @database_sync_to_async
    def update_user_profile(self, user_id, profile_data):
        """Update user profile"""
        try:
            user = User.objects.get(id=user_id)
            
            # Update allowed fields
            allowed_fields = ['name', 'email', 'gender']
            updated_fields = []
            
            for field in allowed_fields:
                if field in profile_data:
                    setattr(user, field, profile_data[field])
                    updated_fields.append(field)
            
            if updated_fields:
                user.save(update_fields=updated_fields)
                
                return {
                    'success': True,
                    'data': {
                        'id': user.id,
                        'name': user.name,
                        'email': user.email,
                        'gender': user.gender
                    }
                }
            else:
                return {'success': False, 'message': 'No valid fields to update'}
                
        except User.DoesNotExist:
            return {'success': False, 'message': 'User not found'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    async def send_error(self, message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
            'timestamp': timezone.now().isoformat(),
            'status': 'error'
        }))