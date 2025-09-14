from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/executives/(?P<user_id>\w+)/$', consumers.ExecutivesListConsumer.as_asgi()),
]
