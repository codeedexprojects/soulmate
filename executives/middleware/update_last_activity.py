from django.utils import timezone
from executives.models import Executives

class UpdateLastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        executive_id = request.session.get('executive_id')
        if executive_id:
            try:
                executive = Executives.objects.get(id=executive_id)
                executive.last_activity = timezone.now()
                executive.save(update_fields=['last_activity'])
            except Executives.DoesNotExist:
                pass
        return response
