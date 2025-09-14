from django.urls import path
from .consumers import CallsConsumer

websocket_urlpatterns = [
    path('ws/calls-management/', CallsConsumer.as_asgi()),  # New calls management consumer
]