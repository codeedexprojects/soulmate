from django.urls import path
from .consumers import ExecutivesListConsumer

websocket_urlpatterns = [
    path('ws/executives/<int:user_id>/', ExecutivesListConsumer.as_asgi()),
]