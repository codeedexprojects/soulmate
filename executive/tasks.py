from celery import shared_task
from .models import CallHistory

@shared_task
def deduct_coins(call_id):
    try:
        call_history = CallHistory.objects.get(id=call_id)
        user = call_history.user
        executive = call_history.executive
        call_duration_seconds = call_history.get_duration_in_seconds()

        # Deduct coins for the call
        total_deduction = call_duration_seconds * 3
        user.coin_balance -= total_deduction
        user.save()

        # Add coins to the executive
        executive.coins_balance += total_deduction
        executive.save()

        return f"Call processed: {call_id}"
    except Exception as e:
        return f"Error: {e}"
