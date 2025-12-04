from django.contrib import admin
from .models import *


# If Notification model exists, uncomment and register below:
# @admin.register(Notification)
# class NotificationAdmin(admin.ModelAdmin):
#     list_display = ('id', 'created_at')
#     list_filter = ('created_at',)
#     search_fields = ('id',)
#     readonly_fields = ('created_at',)
#     ordering = ('-created_at',)
