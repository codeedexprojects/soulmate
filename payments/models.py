from django.db import models
from decimal import Decimal
from users.models import User
from django.utils import timezone

class RechargePlanCato(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class RechargePlan(models.Model):
    plan_name = models.CharField(max_length=100)
    total_talktime = models.CharField(max_length=100)
    coin_package = models.PositiveIntegerField()
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.FloatField(default=0)
    category_id = models.ForeignKey(RechargePlanCato, on_delete=models.CASCADE, related_name='recharge_plans', default=1)

    def calculate_discount(self):
        return self.base_price * Decimal(self.discount_percentage / 100)

    def calculate_final_price(self):
        return self.base_price - self.calculate_discount()
    
    def calculate_talk_time_minutes(self):
        return self.coin_package / 180

    def __str__(self):
        return self.plan_name


class Sale(models.Model):
    package = models.ForeignKey(RechargePlan, on_delete=models.CASCADE)
    amount = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    
class PurchaseHistories(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recharge_plan = models.ForeignKey(RechargePlan, on_delete=models.CASCADE)
    coins_purchased = models.IntegerField()
    purchased_price = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_date = models.DateTimeField(auto_now_add=True)
    razorpay_order_id = models.CharField(max_length=100)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    payment_status = models.CharField(max_length=20, choices=[('PENDING', 'Pending'), ('SUCCESS', 'Success')])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} - {self.recharge_plan} - {self.coins_purchased} coins'

    
class CoinConversion(models.Model):
    coins_earned = models.PositiveBigIntegerField()
    rupees = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.coins_earned} coins = ₹{self.rupees}"
    
class PaymentTransaction(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_id = models.CharField(max_length=100, unique=True)
    cf_order_id = models.CharField(max_length=100, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, null=True)
    payment_mode = models.CharField(max_length=50, null=True)
    signature = models.CharField(max_length=256, null=True)