# users/auth_backends.py

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from analytics.models import Admins
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

class AdminAuthBackend(ModelBackend):
    """Custom backend to authenticate Admin users"""
    
    def authenticate(self, request, email=None, password=None, **kwargs):
        """Authenticate admin user by email"""
        try:
            # Try to get admin by email
            admin = Admins.objects.get(email=email)
            
            # Check password
            if admin.check_password(password) and admin.is_active:
                logger.info(f'Admin login successful: {email}')
                return admin
            else:
                logger.warning(f'Admin login failed: invalid password for {email}')
                return None
                
        except Admins.DoesNotExist:
            logger.warning(f'Admin login failed: {email} not found')
            # Run the default password hasher once to reduce timing
            # difference between an existing and nonexistent user
            User().set_password(password)
            return None
    
    def get_user(self, user_id):
        """Get user by ID"""
        try:
            return Admins.objects.get(pk=user_id)
        except Admins.DoesNotExist:
            return None
