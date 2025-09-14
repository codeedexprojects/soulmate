from django.urls import path
from .consumers import CallConsumer, CallsConsumer

websocket_urlpatterns = [
    path('ws/calls/', CallConsumer.as_asgi()),
    path('ws/calls-management/', CallsConsumer.as_asgi()),  # New calls management consumer
]