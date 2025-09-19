# asgi.py (UPDATED)
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soulmate.settings')

django_asgi_app = get_asgi_application()

# Import all websocket URL patterns
from calls.routing import websocket_urlpatterns as calls_websockets
from executives.routing import websocket_urlpatterns as executives_websockets
from users.routing import websocket_urlpatterns as users_websockets

# Combine all websocket patterns
websocket_urlpatterns = calls_websockets + executives_websockets + users_websockets

from .middleware import NoAuthMiddlewareStack

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': NoAuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})