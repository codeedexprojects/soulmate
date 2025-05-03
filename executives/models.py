from django.db import models

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils import timezone
from users.models import *
from django.utils.timezone import now
from analytics.models import Admins
from datetime import timedelta

class ExecutiveManager(BaseUserManager):
    def create_user(self, mobile_number, name, email_id, password=None, **extra_fields):
        if not mobile_number:
            raise ValueError('The Mobile Number field must be set')
        if not email_id:
            raise ValueError('The Email field must be set')

        email_id = self.normalize_email(email_id)
        user = self.model(mobile_number=mobile_number, name=name, email_id=email_id, **extra_fields)

        if password:
            user.password = password

        user.save(using=self._db)
        return user

    def create_superuser(self, mobile_number, name, email_id, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(mobile_number, name, email_id, password, **extra_fields)


class Executives(AbstractBaseUser):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('others', 'Others'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    name = models.CharField(max_length=100)
    mobile_number = models.CharField(max_length=15, unique=True, db_index=True)
    email_id = models.EmailField(max_length=255, unique=True)
    password = models.CharField(max_length=128)
    age = models.PositiveIntegerField()
    # created_by = models.ForeignKey('analytics.Admins', on_delete=models.SET_NULL, null=True, blank=True)
    online = models.BooleanField(default=False)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='male')
    coins_per_second = models.FloatField(default=3)
    education_qualification = models.CharField(max_length=255, null=True, blank=True)
    profession = models.CharField(max_length=255, null=True, blank=True)
    skills = models.TextField(null=True, blank=True)
    place = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    executive_id = models.CharField(max_length=50, unique=True)
    set_coin = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    coins_balance = models.IntegerField(default=0)
    duty_start_time = models.DateTimeField(null=True, blank=True)
    total_on_duty_seconds = models.PositiveIntegerField(default=0)
    total_talk_seconds_today = models.PositiveIntegerField(default=0)
    total_picked_calls = models.PositiveIntegerField(default=0)
    total_missed_calls = models.PositiveIntegerField(default=0)
    is_banned = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    user_id = models.OneToOneField('users.User', on_delete=models.CASCADE, null=True, blank=True, default=None)
    on_call = models.BooleanField(default=False)
    manager_executive = models.ForeignKey('analytics.Admins', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_executives')
    device_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = ExecutiveManager()
    otp = models.CharField(max_length=6, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)
    current_session_key = models.CharField(max_length=40, blank=True, null=True) 
    is_logged_out = models.BooleanField(default=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    AUTO_LOGOUT_MINUTES = 3600
    
    USERNAME_FIELD = 'mobile_number' 
    REQUIRED_FIELDS = ['name', 'email_id']  

    class Meta:
        verbose_name = "Executive"
        verbose_name_plural = "Executives"

    def __str__(self):
        return self.name

    def start_duty(self):
        if not self.online:
            self.online = True
            self.duty_start_time = timezone.now()
            self.save()

    def end_duty(self):
        if self.online and self.duty_start_time:
            time_diff = timezone.now() - self.duty_start_time
            self.total_on_duty_seconds += time_diff.total_seconds()
            self.online = False
            self.duty_start_time = None
            self.save()

    def increment_picked_calls(self):
        self.total_picked_calls += 1
        self.save()

    def increment_missed_calls(self):
        self.total_missed_calls += 1
        self.save()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
    
    def save(self, *args, **kwargs):
        if not self.online and self.duty_start_time:
            self.total_on_duty_seconds += (timezone.now() - self.duty_start_time).total_seconds()
            self.duty_start_time = None 
        elif self.online and not self.duty_start_time:
            self.duty_start_time = timezone.now()  
        super().save(*args, **kwargs)

    def save(self, *args, **kwargs):
        if not self.executive_id:
            last_executive = Executives.objects.order_by('-id').first()
            if last_executive and last_executive.executive_id.startswith('BTEX'):
                last_number = int(last_executive.executive_id[4:]) 
                self.executive_id = f'BTEX{last_number + 1}'
            else:
                self.executive_id = 'BTEX1000'  

        if not self.online and self.duty_start_time:
            self.total_on_duty_seconds += (timezone.now() - self.duty_start_time).total_seconds()
            self.duty_start_time = None  
        elif self.online and not self.duty_start_time:
            self.duty_start_time = timezone.now()  

        super().save(*args, **kwargs)

    def check_activity_timeout(self):
        if not self.last_activity:
            return False
        timeout_duration = timedelta(minutes=self.AUTO_LOGOUT_MINUTES)
        return timezone.now() - self.last_activity > timeout_duration

class BlockedDevices(models.Model):
    device_id = models.CharField(max_length=255, unique=True)
    is_banned = models.BooleanField(default=False)

    def __str__(self):
        return f"Device {self.device_id} - {'Banned' if self.is_banned else 'Allowed'}"

class ExecutiveProfilePicture(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    executive = models.OneToOneField(Executives, on_delete=models.CASCADE)
    profile_photo = models.ImageField(upload_to='executive_pictures/')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def approve(self):
        self.status = 'approved'
        self.save()

    def reject(self):
        self.status = 'rejected'
        self.save()



class LoginActivity(models.Model):
    executive = models.ForeignKey(Executives, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    device_id = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
