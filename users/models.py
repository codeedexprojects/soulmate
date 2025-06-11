from django.db import models
from executives.models import Executives
from django.conf import settings
from decimal import Decimal
import random
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
from executives.models import Executives
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils.timezone import now
from django.db import transaction


class CustomUserManager(BaseUserManager):
    def create_user(self, mobile_number, password=None, **extra_fields):
        if not mobile_number:
            raise ValueError('The Mobile Number field must be set')
        user = self.model(mobile_number=mobile_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, mobile_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(mobile_number, password, **extra_fields)

class User(AbstractBaseUser):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=100, blank=True, null=True)
    mobile_number = models.CharField(max_length=15, unique=True)
    dp_image = models.ImageField(upload_to='user/dp_images/', blank=True, null=True)
    otp = models.CharField(max_length=6, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    gender = models.CharField(max_length=8, choices=GENDER_CHOICES, blank=True, null=True)
    coin_balance = models.PositiveIntegerField(default=0)
    user_id = models.CharField(max_length=10, unique=True, editable=False)
    last_login = models.DateTimeField(null=True, blank=True)
    is_banned = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    is_dormant = models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True) 
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'mobile_number'
    REQUIRED_FIELDS = ['name']  

    objects = CustomUserManager()

    PREFIX = "BST"

    def save(self, *args, **kwargs):
        if not self.user_id:
            latest_user = User.objects.filter(user_id__startswith=self.PREFIX).order_by('-user_id').first()
            
            if latest_user and latest_user.user_id:
                last_number = int(latest_user.user_id[len(self.PREFIX):])
                new_number = last_number + 1
            else:
                new_number = 1000
            
            self.user_id = f"{self.PREFIX}{new_number}"
        
        super().save(*args, **kwargs)

    def add_coins(self, coins):
        self.coin_balance += coins
        self.save()

    def mark_as_dormant(self):
        if self.last_login:
            days_since_last_login = (timezone.now() - self.last_login).days
            if days_since_last_login > 59:
                self.is_dormant = True
                self.save()
        else:
            self.is_dormant = True
            self.save()

    def mark_as_online(self):
        if self.last_login:
            time_since_last_login = timezone.now() - self.last_login
            if time_since_last_login <= timedelta(hours=24):
                self.is_online = True
            else:
                self.is_online = False
        else:
            self.is_online = False
        self.save()

    def __str__(self):
        return self.name or self.mobile_number
        
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    coin_balance = models.PositiveIntegerField(default=0)

    def add_coins(self, coins):
        with transaction.atomic():
            # Lock the row for update
            profile = UserProfile.objects.select_for_update().get(pk=self.pk)
            profile.coin_balance += coins
            profile.save()
class Favourite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    executive = models.ForeignKey(Executives, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'executive')

    def __str__(self):
        return f"{self.user} - {self.executive}"


class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    executive = models.ForeignKey(Executives, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField()
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'executive')
    def __str__(self):
        return f"{self.user.username} rated {self.executive.name} - {self.rating}"
    
class CarouselImage(models.Model):
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to='carousel_images/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Career(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]

    MARITAL_STATUS_CHOICES = [
        ('Married', 'Married'),
        ('Single', 'Single'),
    ]

    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15)
    age = models.PositiveIntegerField()
    place = models.CharField(max_length=255)
    education = models.CharField(max_length=255)
    profession = models.CharField(max_length=255)
    spoken_languages = models.CharField(max_length=255, help_text="List languages separated by commas")
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES)
    marital_status = models.CharField(max_length=10, choices=MARITAL_STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.full_name
    
User = get_user_model()

class ReferralCode(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="referral_code")
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return f"{self.user.username}'s referral code: {self.code}"

class ReferralHistory(models.Model):
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="referred_users")
    referred_user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="referred_by")
    recharged = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.referrer.username} referred {self.referred_user.username}"

@receiver(post_save, sender=User)
def create_referral_code(sender, instance, created, **kwargs):
    if created:
        code = f"BT{uuid.uuid4().hex[:6].upper()}"
        ReferralCode.objects.create(user=instance, code=code)

class UserBlock(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_users')
    executive = models.ForeignKey('executives.Executives', on_delete=models.CASCADE, related_name='blocked_executives')
    is_blocked = models.BooleanField(default=False)
    reason = models.TextField()
    blocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'executive')

    def __str__(self):
        return f"{self.user.user_id} blocked {self.executive.executive_id}"
    
class DeletedUser(models.Model):
    mobile_number = models.CharField(max_length=15, unique=True)
    deleted_at = models.DateTimeField(auto_now_add=True)