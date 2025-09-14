# calls/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import AgoraCallHistory, CallRating
from users.models import CarouselImage
from users.serializers import CarouselImageSerializer
from .serializers import CallRatingSerializer
from users.models import User
from executives.models import Executives


class CallsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            # Accept the connection
            await self.accept()
            
            # Send connection confirmation
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Calls WebSocket connected successfully!',
                'timestamp': timezone.now().isoformat(),
                'status': 'connected'
            }))
            
            print(f"Calls WebSocket: Connection established")
            
        except Exception as e:
            print(f"Calls WebSocket connection error: {e}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        print(f"Calls WebSocket disconnected with code: {close_code}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            print(f"Received Calls WebSocket message: {data}")
            
            # Connection and utility messages
            if message_type == 'ping':
                await self.handle_ping()
                
            elif message_type == 'test_connection':
                await self.handle_test_connection()
                
            # Carousel image management
            elif message_type == 'get_carousel_images':
                await self.handle_get_carousel_images()
                
            elif message_type == 'create_carousel_image':
                await self.handle_create_carousel_image(data)
                
            elif message_type == 'update_carousel_image':
                await self.handle_update_carousel_image(data)
                
            elif message_type == 'delete_carousel_image':
                await self.handle_delete_carousel_image(data)
                
            # Call status management
            elif message_type == 'get_call_status':
                await self.handle_get_call_status(data)
                
            elif message_type == 'get_call_history':
                await self.handle_get_call_history(data)
                
            elif message_type == 'get_user_call_history':
                await self.handle_get_user_call_history(data)
                
            elif message_type == 'get_executive_call_history':
                await self.handle_get_executive_call_history(data)
                
            # Call rating management
            elif message_type == 'create_rating':
                await self.handle_create_rating(data)
                
            elif message_type == 'get_call_ratings':
                await self.handle_get_call_ratings(data)
                
            elif message_type == 'update_rating':
                await self.handle_update_rating(data)
                
            elif message_type == 'delete_rating':
                await self.handle_delete_rating(data)
                
            # Call statistics
            elif message_type == 'get_call_statistics':
                await self.handle_get_call_statistics(data)
                
            else:
                await self.send_error(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            print(f"Error processing Calls WebSocket message: {e}")
            await self.send_error(f"Error processing message: {str(e)}")

    # Utility handlers
    async def handle_ping(self):
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': timezone.now().isoformat(),
            'message': 'Calls WebSocket is working perfectly!'
        }))

    async def handle_test_connection(self):
        await self.send(text_data=json.dumps({
            'type': 'connection_test_response',
            'timestamp': timezone.now().isoformat(),
            'message': 'Calls connection test successful',
            'server_status': 'running',
            'websocket_status': 'connected'
        }))

    # Carousel image handlers
    async def handle_get_carousel_images(self):
        """Handle get carousel images - converted from CarouselImageListCreateView GET"""
        try:
            carousel_data = await self.get_carousel_images()
            await self.send(text_data=json.dumps({
                'type': 'carousel_images',
                'data': carousel_data,
                'timestamp': timezone.now().isoformat(),
                'success': True
            }))
        except Exception as e:
            await self.send_error(f"Error fetching carousel images: {str(e)}")

    async def handle_create_carousel_image(self, data):
        """Handle create carousel image - converted from CarouselImageListCreateView POST"""
        image_data = data.get('image_data')
        if not image_data:
            await self.send_error("image_data is required")
            return
        
        try:
            created_image = await self.create_carousel_image(image_data)
            if 'error' in created_image:
                await self.send_error(created_image['error'])
                return
                
            await self.send(text_data=json.dumps({
                'type': 'carousel_image_created',
                'data': created_image,
                'timestamp': timezone.now().isoformat(),
                'success': True
            }))
        except Exception as e:
            await self.send_error(f"Error creating carousel image: {str(e)}")

    async def handle_update_carousel_image(self, data):
        """Update carousel image"""
        image_id = data.get('image_id')
        image_data = data.get('image_data')
        
        if not image_id or not image_data:
            await self.send_error("image_id and image_data are required")
            return
        
        try:
            updated_image = await self.update_carousel_image(image_id, image_data)
            if 'error' in updated_image:
                await self.send_error(updated_image['error'])
                return
                
            await self.send(text_data=json.dumps({
                'type': 'carousel_image_updated',
                'data': updated_image,
                'timestamp': timezone.now().isoformat(),
                'success': True
            }))
        except Exception as e:
            await self.send_error(f"Error updating carousel image: {str(e)}")

    async def handle_delete_carousel_image(self, data):
        """Delete carousel image"""
        image_id = data.get('image_id')
        if not image_id:
            await self.send_error("image_id is required")
            return
        
        try:
            result = await self.delete_carousel_image(image_id)
            await self.send(text_data=json.dumps({
                'type': 'carousel_image_deleted',
                'image_id': image_id,
                'message': result['message'],
                'timestamp': timezone.now().isoformat(),
                'success': result['success']
            }))
        except Exception as e:
            await self.send_error(f"Error deleting carousel image: {str(e)}")

    # Call status handlers
    async def handle_get_call_status(self, data):
        """Handle get call status - converted from GetCallStatusView"""
        call_id = data.get('call_id')
        if not call_id:
            await self.send_error("call_id is required")
            return
        
        try:
            call_status_data = await self.get_call_status(call_id)
            if not call_status_data:
                await self.send_error("Invalid call_id")
                return
                
            await self.send(text_data=json.dumps({
                'type': 'call_status',
                'call_id': call_id,
                'data': call_status_data,
                'timestamp': timezone.now().isoformat(),
                'success': True
            }))
        except Exception as e:
            await self.send_error(f"Error fetching call status: {str(e)}")

    async def handle_get_call_history(self, data):
        """Get all call history with optional filters"""
        filters = data.get('filters', {})
        limit = data.get('limit', 50)
        offset = data.get('offset', 0)
        
        try:
            call_history_data = await self.get_call_history(filters, limit, offset)
            await self.send(text_data=json.dumps({
                'type': 'call_history',
                'data': call_history_data,
                'filters': filters,
                'timestamp': timezone.now().isoformat(),
                'success': True
            }))
        except Exception as e:
            await self.send_error(f"Error fetching call history: {str(e)}")

    async def handle_get_user_call_history(self, data):
        """Get call history for specific user"""
        user_id = data.get('user_id')
        if not user_id:
            await self.send_error("user_id is required")
            return
        
        limit = data.get('limit', 20)
        offset = data.get('offset', 0)
        
        try:
            call_history_data = await self.get_user_call_history(user_id, limit, offset)
            await self.send(text_data=json.dumps({
                'type': 'user_call_history',
                'user_id': user_id,
                'data': call_history_data,
                'timestamp': timezone.now().isoformat(),
                'success': True
            }))
        except Exception as e:
            await self.send_error(f"Error fetching user call history: {str(e)}")

    async def handle_get_executive_call_history(self, data):
        """Get call history for specific executive"""
        executive_id = data.get('executive_id')
        if not executive_id:
            await self.send_error("executive_id is required")
            return
        
        limit = data.get('limit', 20)
        offset = data.get('offset', 0)
        
        try:
            call_history_data = await self.get_executive_call_history(executive_id, limit, offset)
            await self.send(text_data=json.dumps({
                'type': 'executive_call_history',
                'executive_id': executive_id,
                'data': call_history_data,
                'timestamp': timezone.now().isoformat(),
                'success': True
            }))
        except Exception as e:
            await self.send_error(f"Error fetching executive call history: {str(e)}")

    # Rating handlers
    async def handle_create_rating(self, data):
        """Create call rating"""
        rating_data = data.get('rating_data')
        if not rating_data:
            await self.send_error("rating_data is required")
            return
        
        try:
            created_rating = await self.create_call_rating(rating_data)
            if 'error' in created_rating:
                await self.send_error(created_rating['error'])
                return
                
            await self.send(text_data=json.dumps({
                'type': 'rating_created',
                'data': created_rating,
                'timestamp': timezone.now().isoformat(),
                'success': True
            }))
        except Exception as e:
            await self.send_error(f"Error creating rating: {str(e)}")

    async def handle_get_call_ratings(self, data):
        """Get ratings for a specific call or executive"""
        call_id = data.get('call_id')
        executive_id = data.get('executive_id')
        
        if not call_id and not executive_id:
            await self.send_error("Either call_id or executive_id is required")
            return
        
        try:
            ratings_data = await self.get_call_ratings(call_id, executive_id)
            await self.send(text_data=json.dumps({
                'type': 'call_ratings',
                'call_id': call_id,
                'executive_id': executive_id,
                'data': ratings_data,
                'timestamp': timezone.now().isoformat(),
                'success': True
            }))
        except Exception as e:
            await self.send_error(f"Error fetching ratings: {str(e)}")

    async def handle_update_rating(self, data):
        """Update call rating"""
        rating_id = data.get('rating_id')
        rating_data = data.get('rating_data')
        
        if not rating_id or not rating_data:
            await self.send_error("rating_id and rating_data are required")
            return
        
        try:
            updated_rating = await self.update_call_rating(rating_id, rating_data)
            if 'error' in updated_rating:
                await self.send_error(updated_rating['error'])
                return
                
            await self.send(text_data=json.dumps({
                'type': 'rating_updated',
                'data': updated_rating,
                'timestamp': timezone.now().isoformat(),
                'success': True
            }))
        except Exception as e:
            await self.send_error(f"Error updating rating: {str(e)}")

    async def handle_delete_rating(self, data):
        """Delete call rating"""
        rating_id = data.get('rating_id')
        if not rating_id:
            await self.send_error("rating_id is required")
            return
        
        try:
            result = await self.delete_call_rating(rating_id)
            await self.send(text_data=json.dumps({
                'type': 'rating_deleted',
                'rating_id': rating_id,
                'message': result['message'],
                'timestamp': timezone.now().isoformat(),
                'success': result['success']
            }))
        except Exception as e:
            await self.send_error(f"Error deleting rating: {str(e)}")

    async def handle_get_call_statistics(self, data):
        """Get call statistics"""
        user_id = data.get('user_id')
        executive_id = data.get('executive_id')
        date_range = data.get('date_range')  # {'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}
        
        try:
            stats_data = await self.get_call_statistics(user_id, executive_id, date_range)
            await self.send(text_data=json.dumps({
                'type': 'call_statistics',
                'user_id': user_id,
                'executive_id': executive_id,
                'date_range': date_range,
                'data': stats_data,
                'timestamp': timezone.now().isoformat(),
                'success': True
            }))
        except Exception as e:
            await self.send_error(f"Error fetching call statistics: {str(e)}")

    # Database operations
    @database_sync_to_async
    def get_carousel_images(self):
        """Get all carousel images"""
        try:
            images = CarouselImage.objects.all()
            serializer = CarouselImageSerializer(images, many=True, context={'request': None})
            return serializer.data
        except Exception as e:
            raise Exception(f"Error fetching carousel images: {str(e)}")

    @database_sync_to_async
    def create_carousel_image(self, image_data):
        """Create new carousel image"""
        try:
            serializer = CarouselImageSerializer(data=image_data, context={'request': None})
            if serializer.is_valid():
                serializer.save()
                return serializer.data
            else:
                return {'error': serializer.errors}
        except Exception as e:
            return {'error': str(e)}

    @database_sync_to_async
    def update_carousel_image(self, image_id, image_data):
        """Update carousel image"""
        try:
            image = CarouselImage.objects.get(id=image_id)
            serializer = CarouselImageSerializer(image, data=image_data, partial=True, context={'request': None})
            if serializer.is_valid():
                serializer.save()
                return serializer.data
            else:
                return {'error': serializer.errors}
        except CarouselImage.DoesNotExist:
            return {'error': 'Image not found'}
        except Exception as e:
            return {'error': str(e)}

    @database_sync_to_async
    def delete_carousel_image(self, image_id):
        """Delete carousel image"""
        try:
            deleted_count = CarouselImage.objects.filter(id=image_id).delete()[0]
            if deleted_count > 0:
                return {'success': True, 'message': 'Image deleted successfully'}
            else:
                return {'success': False, 'message': 'Image not found'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    @database_sync_to_async
    def get_call_status(self, call_id):
        """Get call status by call_id"""
        try:
            call_history = AgoraCallHistory.objects.get(id=call_id)
            return {
                "status": call_history.status,
                "executive_id": call_history.executive.id,
                "user_id": call_history.user.id,
                "gender": call_history.user.gender,
                "user": call_history.user.user_id,
                "token": call_history.token,
                "call_id": call_history.id,
                "executive_token": call_history.executive_token,
            }
        except AgoraCallHistory.DoesNotExist:
            return None
        except Exception as e:
            raise Exception(f"Error fetching call status: {str(e)}")

    @database_sync_to_async
    def get_call_history(self, filters, limit, offset):
        """Get call history with filters"""
        try:
            queryset = AgoraCallHistory.objects.all()
            
            # Apply filters
            if 'status' in filters:
                queryset = queryset.filter(status=filters['status'])
            if 'user_id' in filters:
                queryset = queryset.filter(user_id=filters['user_id'])
            if 'executive_id' in filters:
                queryset = queryset.filter(executive_id=filters['executive_id'])
            if 'date_from' in filters:
                queryset = queryset.filter(start_time__gte=filters['date_from'])
            if 'date_to' in filters:
                queryset = queryset.filter(start_time__lte=filters['date_to'])
            
            # Order and paginate
            queryset = queryset.order_by('-start_time')[offset:offset+limit]
            
            # Convert to list of dicts
            data = []
            for call in queryset:
                data.append({
                    'id': call.id,
                    'status': call.status,
                    'user_id': call.user.id,
                    'executive_id': call.executive.id,
                    'channel_name': call.channel_name,
                    'start_time': call.start_time.isoformat(),
                    'end_time': call.end_time.isoformat() if call.end_time else None,
                    'duration': call.duration if hasattr(call, 'duration') else None
                })
            
            return data
        except Exception as e:
            raise Exception(f"Error fetching call history: {str(e)}")

    @database_sync_to_async
    def get_user_call_history(self, user_id, limit, offset):
        """Get call history for specific user"""
        try:
            calls = AgoraCallHistory.objects.filter(
                user_id=user_id
            ).order_by('-start_time')[offset:offset+limit]
            
            data = []
            for call in calls:
                data.append({
                    'id': call.id,
                    'status': call.status,
                    'executive_id': call.executive.id,
                    'executive_name': getattr(call.executive, 'name', 'Unknown'),
                    'channel_name': call.channel_name,
                    'start_time': call.start_time.isoformat(),
                    'end_time': call.end_time.isoformat() if call.end_time else None,
                    'duration': call.duration if hasattr(call, 'duration') else None
                })
            
            return data
        except Exception as e:
            raise Exception(f"Error fetching user call history: {str(e)}")

    @database_sync_to_async
    def get_executive_call_history(self, executive_id, limit, offset):
        """Get call history for specific executive"""
        try:
            calls = AgoraCallHistory.objects.filter(
                executive_id=executive_id
            ).order_by('-start_time')[offset:offset+limit]
            
            data = []
            for call in calls:
                data.append({
                    'id': call.id,
                    'status': call.status,
                    'user_id': call.user.id,
                    'user_name': getattr(call.user, 'name', 'Unknown'),
                    'channel_name': call.channel_name,
                    'start_time': call.start_time.isoformat(),
                    'end_time': call.end_time.isoformat() if call.end_time else None,
                    'duration': call.duration if hasattr(call, 'duration') else None
                })
            
            return data
        except Exception as e:
            raise Exception(f"Error fetching executive call history: {str(e)}")

    @database_sync_to_async
    def create_call_rating(self, rating_data):
        """Create call rating"""
        try:
            serializer = CallRatingSerializer(data=rating_data)
            if serializer.is_valid():
                serializer.save()
                return serializer.data
            else:
                return {'error': serializer.errors}
        except Exception as e:
            return {'error': str(e)}

    @database_sync_to_async
    def get_call_ratings(self, call_id=None, executive_id=None):
        """Get ratings for call or executive"""
        try:
            if call_id:
                ratings = CallRating.objects.filter(call_id=call_id)
            elif executive_id:
                ratings = CallRating.objects.filter(executive_id=executive_id)
            else:
                ratings = CallRating.objects.all()
            
            serializer = CallRatingSerializer(ratings, many=True)
            return serializer.data
        except Exception as e:
            raise Exception(f"Error fetching ratings: {str(e)}")

    @database_sync_to_async
    def update_call_rating(self, rating_id, rating_data):
        """Update call rating"""
        try:
            rating = CallRating.objects.get(id=rating_id)
            serializer = CallRatingSerializer(rating, data=rating_data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return serializer.data
            else:
                return {'error': serializer.errors}
        except CallRating.DoesNotExist:
            return {'error': 'Rating not found'}
        except Exception as e:
            return {'error': str(e)}

    @database_sync_to_async
    def delete_call_rating(self, rating_id):
        """Delete call rating"""
        try:
            deleted_count = CallRating.objects.filter(id=rating_id).delete()[0]
            if deleted_count > 0:
                return {'success': True, 'message': 'Rating deleted successfully'}
            else:
                return {'success': False, 'message': 'Rating not found'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    @database_sync_to_async
    def get_call_statistics(self, user_id=None, executive_id=None, date_range=None):
        """Get call statistics"""
        try:
            from django.db.models import Count, Avg, Sum
            from datetime import datetime
            
            queryset = AgoraCallHistory.objects.all()
            
            # Apply filters
            if user_id:
                queryset = queryset.filter(user_id=user_id)
            if executive_id:
                queryset = queryset.filter(executive_id=executive_id)
            if date_range:
                if 'start' in date_range:
                    start_date = datetime.strptime(date_range['start'], '%Y-%m-%d')
                    queryset = queryset.filter(start_time__gte=start_date)
                if 'end' in date_range:
                    end_date = datetime.strptime(date_range['end'], '%Y-%m-%d')
                    queryset = queryset.filter(start_time__lte=end_date)
            
            # Calculate statistics
            total_calls = queryset.count()
            
            status_counts = queryset.values('status').annotate(
                count=Count('status')
            )
            
            # Convert to dict for easier handling
            status_stats = {}
            for item in status_counts:
                status_stats[item['status']] = item['count']
            
            # Calculate average ratings if executive_id is provided
            avg_rating = None
            if executive_id:
                ratings = CallRating.objects.filter(executive_id=executive_id)
                if date_range:
                    if 'start' in date_range:
                        start_date = datetime.strptime(date_range['start'], '%Y-%m-%d')
                        ratings = ratings.filter(created_at__gte=start_date)
                    if 'end' in date_range:
                        end_date = datetime.strptime(date_range['end'], '%Y-%m-%d')
                        ratings = ratings.filter(created_at__lte=end_date)
                
                avg_rating = ratings.aggregate(avg_rating=Avg('stars'))['avg_rating']
            
            return {
                'total_calls': total_calls,
                'status_breakdown': status_stats,
                'average_rating': float(avg_rating) if avg_rating else None,
                'successful_calls': status_stats.get('completed', 0),
                'missed_calls': status_stats.get('missed', 0),
                'rejected_calls': status_stats.get('rejected', 0),
            }
        except Exception as e:
            raise Exception(f"Error fetching call statistics: {str(e)}")

    async def send_error(self, message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
            'timestamp': timezone.now().isoformat(),
            'status': 'error'
        }))