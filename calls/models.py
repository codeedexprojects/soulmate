from django.db import models
from executives.models import Executives
from django.utils.timezone import now
from users.models import User

class AgoraCallHistory(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("joined", "Joined"),
        ("missed", "Missed"),
        ("left", "Left"),
        ("rejected", "rejected"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="caller")
    executive = models.ForeignKey(Executives, on_delete=models.CASCADE, related_name="receiver")
    channel_name = models.CharField(max_length=100)
    executive_token = models.CharField(max_length=300, default="token")
    token = models.CharField(max_length=300, default="token")
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    executive_joined = models.BooleanField(default=False)
    uid = models.IntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    coins_deducted = models.PositiveIntegerField(default=0)
    coins_added = models.PositiveIntegerField(default=0)
    last_coin_update_time = models.DateTimeField(null=True, blank=True) 
    is_active = models.BooleanField(default=True)  

    def __str__(self):
        return f"Call from {self.user} to {self.executive} on {self.channel_name} (Status: {self.status})"

    def calculate_duration(self):

        if self.end_time:
            self.duration = self.end_time - self.start_time
            self.save()

    def update_coin_transfer(self, coins_per_second=3):

        if self.status == "joined" and self.end_time:
            self.calculate_duration()
            total_seconds = int(self.duration.total_seconds())
            coins_to_transfer = total_seconds * coins_per_second

            if self.user.coin_balance < coins_to_transfer:
                coins_to_transfer = self.user.coin_balance

            self.user.coin_balance -= coins_to_transfer
            self.user.save()

            self.executive.coins_balance += coins_to_transfer
            self.executive.save()

            self.coins_deducted = coins_to_transfer
            self.coins_added = coins_to_transfer
            self.save()



    # def end_call(self):

    #     self.end_time = now()
    #     self.is_active = False
    #     self.save()
    #     self.update_coin_transfer()

    def end_call(self):
        self.end_time = timezone.now()
        self.duration = self.end_time - self.start_time
        self.status = "left"
        self.is_active = False
        self.save()
        self.update_coin_transfer()

from django.utils import timezone


class Channel(models.Model):
    name = models.CharField(max_length=255, unique=True) 
    status = models.CharField(max_length=50, choices=[
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('expired', 'Expired'),
    ], default='active')  
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
class CallRating(models.Model):
    executive = models.ForeignKey('executives.Executives', on_delete=models.CASCADE, related_name="call_ratings")
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name="call_ratings")
    execallhistory = models.ForeignKey(AgoraCallHistory, on_delete=models.CASCADE, related_name="ratings")
    stars = models.PositiveSmallIntegerField()
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating for {self.executive} by {self.user} - {self.stars} Stars"
    
class TalkTime(models.Model):
    call_history = models.ForeignKey(AgoraCallHistory, on_delete=models.CASCADE)