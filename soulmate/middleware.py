from django.contrib.auth import get_user_model
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from urllib.parse import parse_qs

User = get_user_model()

@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None

class NoAuthMiddleware(BaseMiddleware):
    def __init__(self, inner):
        super().__init__(inner)

    async def __call__(self, scope, receive, send):
        # Get user_id from query string if provided
        query_string = parse_qs(scope['query_string'].decode())
        user_id = query_string.get('user_id', [None])[0]
        
        if user_id and user_id.isdigit():
            scope['user'] = await get_user(int(user_id))
        else:
            scope['user'] = None
        
        return await super().__call__(scope, receive, send)

def NoAuthMiddlewareStack(inner):
    return NoAuthMiddleware(inner)