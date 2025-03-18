from django.contrib.auth.backends import BaseBackend
from analytics.models import Admins

class AdminAuthBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None):
        try:
            admin = Admins.objects.get(email=email)
            if admin.check_password(password):
                return admin
        except Admins.DoesNotExist:
            return None
        return None

    def get_user(self, admin_id):
        try:
            return Admins.objects.get(pk=admin_id)
        except Admins.DoesNotExist:
            return None
