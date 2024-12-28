from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Count
from .models import UserBlock, User


@receiver(post_save, sender=UserBlock)
def check_user_suspension(sender, instance, created, **kwargs):
    if created and instance.is_blocked:  # Check only when a new block is created
        user = instance.user
        
        # Count how many times this user is blocked
        block_count = UserBlock.objects.filter(user=user, is_blocked=True).count()
        
        # Suspend user if blocked 5 or more times
        if block_count >= 5:
            user.is_suspended = True
            user.save()
