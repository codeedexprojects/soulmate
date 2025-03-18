from django.db import models
from decimal import Decimal
from users.models import User

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

class PurchaseHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recharge_plan = models.ForeignKey(RechargePlan, on_delete=models.CASCADE)
    coins_purchased = models.IntegerField()
    purchase_date = models.DateTimeField(auto_now_add=True)
    purchased_price = models.DecimalField(max_digits=10, decimal_places=2)


    def __str__(self):
        return f'{self.user} - {self.recharge_plan} - {self.coins_purchased} coins'
    
class CoinConversion(models.Model):
    coins_earned = models.PositiveBigIntegerField()
    rupees = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.coins_earned} coins = ₹{self.rupees}"