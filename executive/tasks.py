from background_task import background
from django.utils import timezone
from datetime import timedelta

# Run this task every second
@background(schedule=1)  # Run this task every second
def deduct_coins_during_call(call_history_id, executive_id):
    try:
        # Local import to avoid circular dependency
        from user.models import CallHistory
        from executive.models import Executives

        # Fetch ongoing call and executive
        call_history = CallHistory.objects.get(id=call_history_id, status='accepted')
        executive = Executives.objects.get(id=executive_id)

        coins_per_second = 3  # Deduction rate
        user = call_history.user

        # Check user's balance
        if user.coin_balance < coins_per_second:
            # End call if insufficient balance
            call_history.status = 'ended'
            call_history.end_time = timezone.now()
            call_history.save()

            executive.on_call = False
            executive.save()
            return

        # Deduct coins and update balances
        user.coin_balance -= coins_per_second
        executive.coins_balance += coins_per_second
        user.save()
        executive.save()

        # Reschedule if call is still ongoing
        if call_history.status == 'accepted':
            deduct_coins_during_call(call_history_id, executive_id, schedule=1)
    except CallHistory.DoesNotExist:
        print("CallHistory not found.")
    except Executives.DoesNotExist:
        print("Executive not found.")
    except ImportError as e:
        print(f"ImportError: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")