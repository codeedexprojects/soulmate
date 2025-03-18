from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from analytics.models import Admins

class AdminAuthBackend(BaseBackend):
    """
    Custom authentication backend to authenticate Admins (HR, Managers, Superusers)
    """
    def authenticate(self, request, email=None, password=None, **kwargs):
        try:
            admin = Admins.objects.get(email=email)
            if check_password(password, admin.password):
                return admin  # Return Admins object on successful authentication
        except Admins.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        """Fetch Admin user by ID"""
        try:
            return Admins.objects.get(pk=user_id)
        except Admins.DoesNotExist:
            return None
