from django.db import models

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils import timezone
from user.models import *
from django.utils.timezone import now

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
    user_id = models.OneToOneField('user.User', on_delete=models.CASCADE, null=True, blank=True, default=None)
    on_call = models.BooleanField()


    objects = ExecutiveManager()

    USERNAME_FIELD = 'mobile_number'  # or 'email', depending on your setup
    REQUIRED_FIELDS = ['name', 'email_id']  # Adjust to include fields needed for superuser creation

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
        if not self.online and self.duty_start_time:
            self.total_on_duty_seconds += (timezone.now() - self.duty_start_time).total_seconds()
            self.duty_start_time = None  # Clear duty start time
        elif self.online and not self.duty_start_time:
            self.duty_start_time = timezone.now()  # Start duty time if online
        super().save(*args, **kwargs)

    def save(self, *args, **kwargs):
        # Auto-generate executive_id if not provided
        if not self.executive_id:
            last_executive = Executives.objects.order_by('-id').first()
            if last_executive and last_executive.executive_id.startswith('BTEX'):
                # Extract the numeric part and increment
                last_number = int(last_executive.executive_id[4:])  # Extract number after 'BTEX'
                self.executive_id = f'BTEX{last_number + 1}'
            else:
                self.executive_id = 'BTEX1000'  # Default start

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


class TalkTime(models.Model):
    call_history = models.ForeignKey('user.AgoraCallHistory', on_delete=models.CASCADE)
    
    

class AdminManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)

class Admins(AbstractBaseUser):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)
    is_staff = models.BooleanField(default=False)
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
    executive = models.ForeignKey('Executives', on_delete=models.CASCADE)
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


class CoinConversion(models.Model):
    coins_earned = models.PositiveBigIntegerField()
    rupees = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.coins_earned} coins = ₹{self.rupees}"

class CallRating(models.Model):
    executive = models.ForeignKey('Executives', on_delete=models.CASCADE, related_name="call_ratings")
    user = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name="call_ratings")
    execallhistory = models.ForeignKey('user.AgoraCallHistory', on_delete=models.CASCADE, related_name="ratings")
    stars = models.PositiveSmallIntegerField()
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating for {self.executive} by {self.user} - {self.stars} Stars"