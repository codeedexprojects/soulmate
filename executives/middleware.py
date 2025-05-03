from django.utils import timezone
from django.contrib.sessions.models import Session
from .models import Executives
from django.http import HttpResponseRedirect 

class AutoLogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not hasattr(request, 'session'):
            return self.get_response(request)

        executive_id = request.session.get('executive_id')
        if executive_id:
            try:
                executive = Executives.objects.get(id=executive_id)
                
                if executive.check_activity_timeout():
                    executive.online = False
                    executive.is_logged_out = True
                    executive.current_session_key = None
                    executive.save()
                    
                    if request.session.session_key:
                        Session.objects.filter(session_key=request.session.session_key).delete()
                    request.session.flush()
                    return HttpResponseRedirect('/login?error=session_expired')  # Redirect to login
                
                executive.last_activity = timezone.now()
                executive.save()
            
            except Executives.DoesNotExist:
                pass  

        return self.get_response(request)