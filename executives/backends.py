from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from analytics.models import Admins

class EmailBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email=email)
            if user.check_password(password):
                return user
        except UserModel.DoesNotExist:
            return None

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None


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
