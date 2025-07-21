from rest_framework.response import Response
from .models import *
from executives.models import *
from .serializers import *
from rest_framework.views import APIView
from rest_framework import generics
from datetime import datetime
from django.db.models import Sum, Count
from django.db.models import Count
from datetime import datetime, timedelta
from django.http import HttpResponse, JsonResponse
from rest_framework import status
from django.shortcuts import get_object_or_404
import razorpay
from calls.models import AgoraCallHistory
from calls.serializers import CoinConversionSerializer
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import hashlib
import json
import logging
from django.utils.decorators import method_decorator
from django.views import View
from django.db import transaction
import requests
from users.models import UserProfile
from django.utils.timezone import localtime

class CreateRechargePlanView(APIView):
    def post(self, request):
        serializer = RechargePlanSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Recharge plan created successfully'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ListRechargePlansView(generics.ListAPIView):
    queryset = RechargePlan.objects.all()
    serializer_class = RechargePlanSerializer

class RechargePlanDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = RechargePlan.objects.all()
    serializer_class = RechargePlanSerializer
    lookup_field = 'id'

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

class RechargeCoinsView(APIView):

    def post(self, request, user_id):
        serializer = RechargeCoinsSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()

            user_profile = get_object_or_404(UserProfile, user_id=user_id)
            user_profile.add_coins(result['coin_package'])

            return Response({
                'message': 'Coins recharged successfully.',
                'coin_package': result['coin_package'],
                'base_amount': result['base_amount'],
                'discount_percentage': result['discount_percentage'],
                'discount_amount': result['discount_amount'],
                'final_amount': result['final_amount'],
                'new_coin_balance': user_profile.coin_balance
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CategoryWithPlansListView(generics.ListAPIView):
    queryset = RechargePlanCato.objects.all()
    serializer_class = CategoryWithPlansSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        response_data = {"Categories": serializer.data}

        return Response(response_data)

class RechargeCoinsByPlanView(APIView):

    def post(self, request, user_id, plan_id):
        plan = get_object_or_404(RechargePlan, id=plan_id)

        plan_serializer = RechargePlanSerializer(plan)

        user_profile = get_object_or_404(UserProfile, user_id=user_id)
        user_profile.add_coins(plan.coin_package)

        return Response({
            'message': 'Coins recharged successfully.',
            'plan_details': plan_serializer.data,
            'new_coin_balance': user_profile.coin_balance
        }, status=status.HTTP_200_OK)

class RechargePlanCategoryListCreateView(generics.ListCreateAPIView):
    queryset = RechargePlanCato.objects.all()
    serializer_class = RechargePlanCategorySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RechargePlanCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = RechargePlanCato.objects.all()
    serializer_class = RechargePlanCategorySerializer

    def retrieve(self, request, *args, **kwargs):
        category = self.get_object()
        serializer = self.get_serializer(category)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        category = self.get_object()
        serializer = self.get_serializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

# somewhere like utils.py or views.py
import razorpay
from django.conf import settings

razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY)
)


# views.py

logger = logging.getLogger(__name__)

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))


class CreateRazorpayOrderView(APIView):
    def post(self, request, user_id, plan_id):
        user = get_object_or_404(User, id=user_id)
        plan = get_object_or_404(RechargePlan, id=plan_id)

        # Calculate amount
        amount = plan.base_price
        amount_in_paise = int(amount * 100)

        # Create Razorpay order
        try:
            razorpay_order = razorpay_client.order.create({
                "amount": amount_in_paise,
                "currency": "INR",
                "receipt": f"recharge_rcpt_{user.id}_{plan.id}",
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Save locally
        PurchaseHistories.objects.create(
            user=user,
            recharge_plan=plan,
            coins_purchased=plan.get_adjusted_coin_package(),
            purchased_price=amount,
            razorpay_order_id=razorpay_order['id'],
            payment_status='FAILED'
        )

        return Response({
            "message": "Order created. Proceed with payment.",
            "razorpay_order_id": razorpay_order['id'],
            "amount": float(amount),
            "currency": "INR",
            "key_id": settings.RAZORPAY_KEY_ID,
            "plan": RechargePlanSerializer(plan).data
        }, status=status.HTTP_201_CREATED)



class GetLatestRazorpayOrderView(APIView):
    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)

        latest_order = PurchaseHistories.objects.filter(
            user=user,
            razorpay_order_id__isnull=False
        ).order_by('-created_at').first()

        if not latest_order:
            return Response({"message": "No Razorpay order found for this user."}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "user_id": user.id,
            "razorpay_order_id": latest_order.razorpay_order_id,
            "payment_status": latest_order.payment_status,
            "amount": float(latest_order.purchased_price),
            "coins_purchased": latest_order.coins_purchased,
            "created_at": latest_order.created_at
        }, status=status.HTTP_200_OK)



class HandlePaymentSuccessView(APIView):
    def post(self, request, razorpay_order_id):
        try:
            payments = razorpay_client.order.payments(razorpay_order_id)
            if not payments['items']:
                return Response({'message': 'No payment linked to this order.'}, status=404)

            payment = payments['items'][0]
            payment_id = payment['id']
            status_razor = payment.get('status')
            amount = payment['amount']

            with transaction.atomic():
                history = PurchaseHistories.objects.select_for_update().get(razorpay_order_id=razorpay_order_id)

                if history.payment_status == 'SUCCESS':
                    return Response({"message": "Payment already completed. Coins already added."}, status=200)

                if status_razor != 'captured':
                    razorpay_client.payment.capture(payment_id, amount)

                history.razorpay_payment_id = payment_id
                history.payment_status = 'SUCCESS'
                history.save()

                user_profile, _ = UserProfile.objects.get_or_create(user=history.user)
                user_profile.add_coins(history.coins_purchased)

            return Response({
                "message": "Payment successful and coins added.",
                "coins_added": history.coins_purchased,
                "current_balance": history.user.coin_balance,
            }, status=200)

        except Exception as e:
            logger.error(f"Payment verification failed for {razorpay_order_id}: {e}")
            return Response({"error": f"Payment verification failed: {str(e)}"}, status=400)



#verify
class VerifyPaymentView(APIView):
    def get(self, request, order_id):
        try:
            payments = razorpay_client.order.payments(order_id)
            history = PurchaseHistories.objects.get(razorpay_order_id=order_id)

            if not payments["items"]:
                # No payment attempt made — likely closed payment window
                if history.payment_status != "FAILED":
                    history.payment_status = "FAILED"
                    history.save()
                return Response({
                    "status": "FAILED",
                    "message": "No payment attempt found. Possibly payment window was closed."
                }, status=200)

            payment = payments["items"][0]
            if payment["status"] == "captured":
                if history.payment_status != "SUCCESS":
                    history.payment_status = "SUCCESS"
                    history.razorpay_payment_id = payment["id"]
                    history.save()

                    user_profile, _ = UserProfile.objects.get_or_create(user=history.user)
                    user_profile.add_coins(history.coins_purchased)

                return Response({
                    "status": "SUCCESS",
                    "message": "Payment verified and coins added."
                }, status=200)
            else:
                # Payment was attempted but not successful
                if history.payment_status != "FAILED":
                    history.payment_status = "FAILED"
                    history.save()
                return Response({
                    "status": "FAILED",
                    "message": f"Payment status from Razorpay: {payment['status']}"
                }, status=200)

        except PurchaseHistories.DoesNotExist:
            return Response({"error": "Order not found in system."}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


#withoutrazorpay
class RechargeCoinsByPlanView(APIView):
    def post(self, request, user_id, plan_id):
        plan = get_object_or_404(RechargePlan, id=plan_id)
        user = get_object_or_404(User, id=user_id)

        # Ensure user has a profile
        user_profile, created = UserProfile.objects.get_or_create(user=user)

        plan_price = plan.calculate_final_price()

        # Add coins to profile and user
        user_profile.add_coins(plan.coin_package)

        PurchaseHistories.objects.create(
            user=user,
            recharge_plan=plan,
            coins_purchased=plan.coin_package,
            purchased_price=plan_price,
            is_admin = True,
            payment_status ='SUCCESS'
        )

        referral_bonus_given = False
        referral_bonus_skipped = False

        if hasattr(user, 'referred_by'): 
            referral_history = user.referred_by
            if not referral_history.recharged: 
                referral_history.recharged = True
                referral_history.save()

                referrer = referral_history.referrer
                referrer_profile, _ = UserProfile.objects.get_or_create(user=referrer)
                referrer_profile.add_coins(300)
                referral_bonus_given = True
            else:
                referral_bonus_skipped = True

        plan_serializer = RechargePlanSerializer(plan)

        response_message = 'Coins recharged successfully.'
        if referral_bonus_given:
            response_message += ' Referral bonus awarded to the referrer.'
        elif referral_bonus_skipped:
            response_message += ' Referral bonus was already awarded.'

        return Response({
            'message': response_message,
            'plan_details': plan_serializer.data,
            'new_coin_balance': user_profile.coin_balance
        }, status=status.HTTP_200_OK)

class PurchaseHistoryListView(generics.ListAPIView):
    serializer_class = PurchaseHistoriesSerializer

    def get_queryset(self):
        return PurchaseHistories.objects.all().order_by('-purchase_date')

class UserPurchaseHistoriesView(APIView):
    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        purchase_history = PurchaseHistories.objects.filter(user=user).order_by('-created_at')
        serializer = PurchaseHistoriesSerializer(purchase_history, many=True)

        return Response({
            'user_id': user_id,
            'purchase_history': serializer.data
        }, status=status.HTTP_200_OK)


class StatisticsAPIView(APIView):

    def get(self, request):
        today = datetime.now().date()

        total_executives = Executives.objects.count()

        total_users = User.objects.count()

        total_revenue = Sale.objects.filter(created_at__date=today).aggregate(total=Sum('amount'))['total'] or 0

        total_sales_today = Sale.objects.filter(created_at__date=today).count()

        total_online_executives = Executives.objects.filter(online=True).count()

        logged_in_today = User.objects.filter(last_login__isnull=False).count()

        total_executives_on_call = AgoraCallHistory.objects.filter(status='joined', end_time__isnull=True).count()

        total_talk_duration = AgoraCallHistory.objects.filter(
            start_time__date=today, is_active=False
        ).aggregate(total_duration=Sum('duration'))['total_duration'] or 0

        data = {
            'total_executives': total_executives,
            'total_users': total_users,
            'total_revenue': total_revenue,
            'total_sales_today': total_sales_today,
            'total_online_executives': total_online_executives,
            'logged_in_today': logged_in_today,
            'total_executives_on_call': total_executives_on_call,
            'total_talk_duration': total_talk_duration,
        }

        return Response(data)
from django.utils.timezone import now, is_naive, make_aware
import pytz

class UserStatisticsAPIView(APIView):
    def get(self, request):
        today = datetime.now().date()
        IST = pytz.timezone('Asia/Kolkata')

        user_data = User.objects.annotate(
            total_coins_spent=Sum('caller__coins_deducted'),
            total_purchases=Count('purchasehistories'),
            total_talktime=Sum('caller__duration'),
        ).select_related('userprofile').values(
            'id', 'user_id', 'mobile_number', 'is_banned', 'is_online',
            'is_suspended', 'is_dormant', 'total_coins_spent',
            'total_purchases', 'total_talktime', 'coin_balance', 'created_at'
        )

        total_users = User.objects.count()
        active_users_count = User.objects.filter(last_login__isnull=False).count()
        inactive_users_count = total_users - active_users_count

        response_data = []
        for user in user_data:
            talktime = user['total_talktime']
            total_seconds = talktime.total_seconds() if isinstance(talktime, timedelta) else (talktime or 0)
            talktime_minutes = total_seconds / 60
            formatted_talktime = (
                f"{int(talktime_minutes)} Mins" if talktime_minutes == int(talktime_minutes)
                else f"{talktime_minutes:.2f} Mins".replace('.00', '')
            )

            created_at = user['created_at']
            if created_at:
                if is_naive(created_at):
                    created_at = make_aware(created_at)
                created_at = created_at.astimezone(IST)
                created_at_str = created_at.strftime('%Y-%m-%d %I:%M:%S %p')
            else:
                created_at_str = None

            # Build user dictionary
            response_data.append({
                'id': user['id'],
                'User_ID': user['user_id'],
                'mobile_number': user['mobile_number'],
                'Date': today,
                'Created_At': created_at_str,
                'Ban': user['is_banned'],
                'Suspend': user['is_suspended'],
                'Is_Dormant': user['is_dormant'],
                'is_online': user['is_online'],
                'Total_Coin_Spend': user['total_coins_spent'] or 0,
                'Total_Purchases': user['total_purchases'] or 0,
                'Total_Talktime': formatted_talktime,
                'Total_Talktime_Seconds': total_seconds,
                'Coin_Balance': user['coin_balance'] or 0,
            })

        return Response({
            'total_users': total_users,
            'active_users': active_users_count,
            'inactive_users': inactive_users_count,
            'user_data': response_data,
        })

class UserStatisticsDetailAPIView(APIView):
    def get(self, request, user_id):
        today = datetime.now().date()

        user = get_object_or_404(User, id=user_id)

        user_data = User.objects.filter(id=user.id).annotate(
            total_coins_spent=Sum('caller__coins_deducted'),
            total_purchases=Count('purchasehistories'),#change

            total_talktime=Sum('caller__duration')
        ).values('id', 'user_id', 'mobile_number', 'is_banned', 'is_suspended', 
                 'is_dormant', 'is_online', 'total_coins_spent', 'total_purchases', 'total_talktime','created_at').first()

        response_data = {
            'id': user_data['id'],
            'user_id': user_data['user_id'],
            'mobile_number': user_data['mobile_number'],
            'date': today,
            'created_at': localtime(user_data['created_at']).strftime('%Y-%m-%d %H:%M:%S') if user_data['created_at'] else None,
            'is_banned': user_data['is_banned'],
            'is_suspended': user_data['is_suspended'],
            'is_dormant': user_data['is_dormant'],
            'is_online': user_data['is_online'],
            'total_coins_spent': user_data['total_coins_spent'] or 0,
            'total_purchases': user_data['total_purchases'] or 0,
            'total_talktime': user_data['total_talktime'] or 0,
        }

        return Response(response_data)
    

class RechargePlanListByCategoryView(generics.ListAPIView):
    serializer_class = RechargePlanSerializer

    def get_queryset(self):
        category_id = self.kwargs.get('category_id')
        return RechargePlan.objects.filter(category_id=category_id)

    def list(self, request, *args, **kwargs):
        category_id = self.kwargs.get('category_id')

        try:
            category = RechargePlanCato.objects.get(id=category_id)
        except RechargePlanCato.DoesNotExist:
            return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)

        queryset = self.get_queryset()

        if not queryset.exists():
            return Response({"error": "No plans found for this category"}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(queryset, many=True)

        response_data = [
            {
                "category_name": category.name,
                "plan_id": plan['id'],
                "plan_name": plan['plan_name'],
                "coin_package": plan['coin_package'],
                "base_price": str(plan['base_price']),
                "discount_percentage": plan['discount_percentage'],
                "final_price": str(Decimal(plan['base_price']) - (Decimal(plan['base_price']) * Decimal(plan['discount_percentage']) / Decimal(100))),
                "total_talktime": f"Your plan talktime is {plan['coin_package'] / 180:.0f} minutes"  # Add total_talktime
            }
            for plan in serializer.data
        ]

        return Response(response_data)
    
class CoinConversionListCreateView(generics.ListCreateAPIView):
    queryset = CoinConversion.objects.all()
    serializer_class = CoinConversionSerializer

    def perform_create(self, serializer):
        coins = self.request.data.get('coins_earned')
        rupees = self.calculate_rupees(coins)
        serializer.save(rupees=rupees)

    # def calculate_rupees(self, coins):
    #     # Replace this with your actual conversion logic
    #     return float(coins) * 0.5  # Example: 1 coin = 0.5 rupee


class CoinConversionUpdateView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CoinConversion.objects.all()
    serializer_class = CoinConversionSerializer

      
    
#CASHFREE_IMPLEMENTATION
import uuid
import requests
from django.conf import settings

#production
# class CreatePaymentLinkView(APIView):
#     def post(self, request, user_id, plan_id):
#         user = get_object_or_404(User, id=user_id)
#         plan = get_object_or_404(RechargePlan, id=plan_id)
#         plan_price = plan.calculate_final_price()

#         order_id = f'ORDER_{uuid.uuid4().hex[:10]}'

#         payload = {
#             "customer_details": {
#                 "customer_id": str(user.id),
#                 "customer_name": user.name,
#                 "customer_phone": user.mobile_number,
#             },
#             "order_id": order_id,
#             "order_amount": float(plan_price),
#             "order_currency": "INR",
#             "order_note": "Coin Recharge",
#         }

#         headers = {
#             "Content-Type": "application/json",
#             "x-api-version": "2022-09-01",
#             "x-client-id": settings.CASHFREE_APP_ID,
#             "x-client-secret": settings.CASHFREE_SECRET_KEY
#         }

#         response = requests.post(
#             f"{settings.CASHFREE_BASE_URL}/orders",
#             json=payload,
#             headers=headers
#         )

#         if response.status_code == 200:
#             payment_data = response.json()

#             session_id = payment_data.get('payment_session_id')
#             if not session_id:
#                 return Response(
#                     {"error": "Missing payment_session_id in Cashfree response", "details": payment_data},
#                     status=status.HTTP_500_INTERNAL_SERVER_ERROR
#                 )

#             payment_link = f"https://www.cashfree.com/checkout/post/{session_id}"

#             # Save purchase history
#             PurchaseHistories.objects.create(
#                 user=user,
#                 recharge_plan=plan,
#                 coins_purchased=plan.coin_package,
#                 purchased_price=plan_price,
#                 payment_status='PENDING',
#                 order_id=order_id,
#                 payment_link=payment_link
#             )

#             return Response({
#                 "order_id": order_id,
#                 "payment_link": payment_link,
#                 "session_id": session_id
#             }, status=status.HTTP_201_CREATED)

#         else:
#             return Response(
#                 {
#                     "error": "Failed to initiate payment",
#                     "cashfree_response": response.json()
#                 },
#                 status=response.status_code
#             )

#test
class CreatePaymentLinkView(APIView):
    def post(self, request, user_id, plan_id):
        user = get_object_or_404(User, id=user_id)
        plan = get_object_or_404(RechargePlan, id=plan_id)
        plan_price = plan.calculate_final_price()

        order_id = f'ORDER_{uuid.uuid4().hex[:10]}'

        payload = {
            "customer_details": {
                "customer_id": str(user.id),
                "customer_name": user.name,
                "customer_phone": user.mobile_number,
            },
            "order_id": order_id,
            "order_amount": float(plan_price),
            "order_currency": "INR",
            "order_note": "Coin Recharge",
        }

        if settings.USE_CASHFREE_SANDBOX:
            base_url = "https://sandbox.cashfree.com/pg"
            app_id = settings.CASHFREE_SANDBOX_APP_ID
            secret_key = settings.CASHFREE_SANDBOX_SECRET_KEY
        else:
            base_url = settings.CASHFREE_BASE_URL
            app_id = settings.CASHFREE_APP_ID
            secret_key = settings.CASHFREE_SECRET_KEY

        headers = {
            "Content-Type": "application/json",
            "x-api-version": "2022-09-01",
            "x-client-id": app_id,
            "x-client-secret": secret_key
        }

        response = requests.post(
            f"{base_url}/orders",
            json=payload,
            headers=headers
        )

        if response.status_code == 200:
            payment_data = response.json()

            session_id = payment_data.get('payment_session_id')
            if not session_id:
                return Response(
                    {"error": "Missing payment_session_id in Cashfree response", "details": payment_data},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            payment_link = f"https://www.cashfree.com/checkout/post/{session_id}"

            PurchaseHistories.objects.create(
                user=user,
                recharge_plan=plan,
                coins_purchased=plan.coin_package,
                purchased_price=plan_price,
                payment_status='PENDING',
                order_id=order_id,
                payment_link=payment_link
            )

            return Response({
                "order_id": order_id,
                "payment_link": payment_link,
                "session_id": session_id
            }, status=status.HTTP_201_CREATED)

        else:
            return Response(
                {
                    "error": "Failed to initiate payment",
                    "cashfree_response": response.json()
                },
                status=response.status_code
            )

from rest_framework.decorators import api_view

@csrf_exempt
@api_view(['POST'])
def cashfree_webhook(request, order_id):
    txn_status = request.data.get('transaction_status')

    try:
        purchase = PurchaseHistories.objects.get(order_id=order_id)
    except PurchaseHistories.DoesNotExist:
        return Response({'message': 'Order not found'}, status=404)

    if txn_status == 'SUCCESS' and purchase.payment_status != 'SUCCESS':
        user = purchase.user
        user.add_coins(purchase.coins_purchased)
        user.save()

        purchase.payment_status = 'SUCCESS'
        purchase.save()

        # Referral logic
        if hasattr(user, 'referred_by'):
            referral_history = user.referred_by
            if not referral_history.recharged:
                referral_history.recharged = True
                referral_history.save()

                referrer = referral_history.referrer
                referrer.add_coins(300)
                referrer.save()

    elif txn_status == 'FAILED':
        purchase.payment_status = 'FAILED'
        purchase.save()

    return Response({'status': 'received'}, status=200)

class GetPaymentDetailsView(APIView):
    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        
        # Get the latest purchase by user (you can order by created_at if available)
        try:
            latest_purchase = PurchaseHistories.objects.filter(user=user).latest('id')  # or 'created_at' if you track time
        except PurchaseHistories.DoesNotExist:
            return Response(
                {"error": "No purchase history found for this user."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            "order_id": latest_purchase.order_id,
            "payment_status": latest_purchase.payment_status,
            "payment_link": latest_purchase.payment_link,
        }, status=status.HTTP_200_OK)
