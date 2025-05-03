from celery import shared_task
from django.utils import timezone
from django.contrib.sessions.models import Session
from .models import Executives

@shared_task
def check_inactive_sessions():
    timeout = timezone.now() - timezone.timedelta(
        minutes=Executives.AUTO_LOGOUT_MINUTES
    )
    
    inactive_executives = Executives.objects.filter(
        last_activity__lt=timeout,
        online=True
    )
    
    for executive in inactive_executives:
        # Update executive status
        executive.online = False
        executive.is_logged_out = True
        executive.current_session_key = None
        executive.save()
        
        # Delete session if exists
        if executive.current_session_key:
            Session.objects.filter(
                session_key=executive.current_session_key
            ).delete()