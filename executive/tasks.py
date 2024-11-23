from celery import shared_task
from django.utils import timezone
from user.models import CallHistory
from .models import ExecutiveCallHistory
# Deduction Task
@shared_task
def deduct_coins_periodically(call_id):
    try:
        user_call_history = CallHistory.objects.get(id=call_id)
        executive = user_call_history.executive
        user = user_call_history.user

        # Ensure the call is still active
        if user_call_history.status == 'accepted':
            # Deduct coins
            user.coin_balance -= 3
            executive.coins_balance += 3

            # Save updated balances
            user.save()
            executive.save()

            # Check if the user still has enough coins
            if user.coin_balance >= 3:
                # Schedule the task to run again in 1 second
                deduct_coins_periodically.apply_async((call_id,), countdown=1)
            else:
                # End the call if the user runs out of coins
                user_call_history.end_time = timezone.now()
                user_call_history.status = 'ended'
                user_call_history.save()

                executive_call_history = ExecutiveCallHistory.objects.get(call_history=user_call_history)
                executive_call_history.end_time = timezone.now()
                executive_call_history.status = 'ended'
                executive_call_history.save()

                executive.on_call = False
                executive.save()

    except CallHistory.DoesNotExist:
        # Handle case where the call record no longer exists
        pass
