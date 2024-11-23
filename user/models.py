from django.db import models
from executive.models import Executives
from django.conf import settings
from decimal import Decimal
import random
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

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
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    name = models.CharField(max_length=100, blank=True, null=True)
    mobile_number = models.CharField(max_length=15, unique=True)
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
    is_active = models.BooleanField(default=True)  # Required by Django for custom users
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'mobile_number'
    REQUIRED_FIELDS = ['name']  # 'mobile_number' is not required here since it's the USERNAME_FIELD

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        if not self.user_id:
            self.user_id = str(random.randint(1000000000, 9999999999))
        super(User, self).save(*args, **kwargs)

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

class RechargePlanCato(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name  

class RechargePlan(models.Model):
    plan_name = models.CharField(max_length=100)
    coin_package = models.PositiveIntegerField()
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.FloatField(default=0)
    category_id = models.ForeignKey(RechargePlanCato, on_delete=models.CASCADE, related_name='recharge_plans', default=1) 

    def calculate_discount(self):
        return self.base_price * Decimal(self.discount_percentage / 100)

    def calculate_final_price(self):
        return self.base_price - self.calculate_discount()

    def __str__(self):
        return self.plan_name


class Sale(models.Model):
    package = models.ForeignKey(RechargePlan, on_delete=models.CASCADE)
    amount = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    coin_balance = models.PositiveIntegerField(default=0)

    def add_coins(self, coins):
        self.coin_balance += coins
        self.save()


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


class CallHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    executive = models.ForeignKey(Executives, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=[('initiated', 'Initiated'), ('accepted', 'Accepted'), ('ended', 'Ended'), ('missed', 'Missed')])
    zegocloud_call_id = models.CharField(max_length=255)

    def __str__(self):
        return f"Call from {self.user.username} to {self.executive.name}"

    def save(self, *args, **kwargs):
        if self.end_time and self.start_time:
            self.duration = self.end_time - self.start_time
            self.is_active = False
            if self.status not in ['accepted', 'ended']:
                self.status = 'missed'
        super(CallHistory, self).save(*args, **kwargs)



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
        ('Unmarried', 'Unmarried'),
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


class PurchaseHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recharge_plan = models.ForeignKey(RechargePlan, on_delete=models.CASCADE)
    coins_purchased = models.IntegerField()
    purchase_date = models.DateTimeField(auto_now_add=True)
    purchased_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)


    def __str__(self):
        return f'{self.user} - {self.recharge_plan} - {self.coins_purchased} coins'
    

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