from django.urls import path
from .consumers import UsersConsumer

websocket_urlpatterns = [
    path('ws/users/', UsersConsumer.as_asgi()),
]
