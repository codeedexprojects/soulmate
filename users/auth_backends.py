from django.contrib.auth.backends import BaseBackend
from analytics.models import Admins
from users.models import User

class AdminAuthBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        try:
            admin = Admins.objects.get(email=email)
            if admin.check_password(password):
                return admin
        except Admins.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        try:
            return Admins.objects.get(pk=user_id)
        except Admins.DoesNotExist:
            return None
