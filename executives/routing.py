from django.urls import re_path
from .consumers import UsersConsumer, ExecutivesConsumer

websocket_urlpatterns = [
    re_path(r'ws/users/$', UsersConsumer.as_asgi()),
    re_path(r'ws/executives/(?P<id>\d+)/$', ExecutivesConsumer.as_asgi()),
]
