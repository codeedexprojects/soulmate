from django.contrib.auth.backends import BaseBackend
from analytics.models import Admins
from django.contrib.auth.hashers import check_password

class AdminAuthBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        """Authenticate an Admin user by email and password"""
        try:
            admin = Admins.objects.get(email=email)
            if check_password(password, admin.password):
                return admin
        except Admins.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        """Get the Admin user instance"""
        try:
            return Admins.objects.get(pk=user_id)
        except Admins.DoesNotExist:
            return None
