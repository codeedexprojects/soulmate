from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from users.models import *
from django.utils.timezone import now

class AdminManager(BaseUserManager):
    
    def create_admin(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        
        admin = self.model(email=email, **extra_fields)
        admin.set_password(password)
        admin.save(using=self._db)
        return admin

    def create_super_admin(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_admin(email, password, **extra_fields)

class Admins(AbstractBaseUser, PermissionsMixin):
    
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)
    
    is_staff = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)

    ROLE_CHOICES = [
        ('hr_user', 'HR - User'),
        ('hr_executive', 'HR - Executive'),
        ('manager_user', 'Manager - User'),
        ('manager_executive', 'Manager - Executive'),
        ('superuser', 'Superuser'),
        ('other', 'Other')
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='other')

    objects = AdminManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return self.email
    
class CoinRedemptionRequest(models.Model):
    executive = models.ForeignKey('executives.Executives', on_delete=models.CASCADE)
    amount_requested = models.DecimalField(max_digits=10, decimal_places=2)
    upi_id = models.CharField(max_length=255)
    request_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.executive} - {self.amount_requested} - {self.status}"



class RevenueTarget(models.Model):
    target_revenue = models.DecimalField(max_digits=10, decimal_places=2)
    target_talktime = models.DurationField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Revenue Target created at {self.created_at}"