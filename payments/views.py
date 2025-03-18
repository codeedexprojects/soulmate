from rest_framework.response import Response
from .models import *
from executives.models import *
from .serializers import *
from rest_framework.views import APIView
from rest_framework import generics
from datetime import datetime
from django.db.models import Sum, Count
from django.db.models import Count
from datetime import datetime
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
import razorpay
from calls.models import AgoraCallHistory
from calls.serializers import CoinConversionSerializer
from django.conf import settings

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

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

class CreateRazorpayOrderView(APIView):
    def post(self, request, user_id, plan_id):
        plan = get_object_or_404(RechargePlan, id=plan_id)

        plan_serializer = RechargePlanSerializer(plan)
        final_amount = plan.calculate_final_price() * 100

        order_data = {
            'amount': int(final_amount),
            'currency': 'INR',
            'payment_capture': 1
        }

        razorpay_order = razorpay_client.order.create(order_data)

        return Response({
            'razorpay_order_id': razorpay_order['id'],
            'amount': razorpay_order['amount'],
            'currency': razorpay_order['currency'],
            'plan_details': plan_serializer.data
        }, status=status.HTTP_201_CREATED)

class HandlePaymentSuccessView(APIView):
    def post(self, request, razorpay_order_id):
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')
        plan_id = request.data.get('plan_id')
        user_id = request.data.get('user_id')

        try:
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }

            razorpay_client.utility.verify_payment_signature(params_dict)
        except razorpay.errors.SignatureVerificationError:
            return Response({'message': 'Payment verification failed.'}, status=status.HTTP_400_BAD_REQUEST)

        plan = get_object_or_404(RechargePlan, id=plan_id)
        user_profile = get_object_or_404(UserProfile, user_id=user_id)

        user_profile.add_coins(plan.coin_package)

        return Response({
            'message': 'Payment successful, coins added to your account.',
            'coin_package': plan.coin_package,
            'new_coin_balance': user_profile.coin_balance
        }, status=status.HTTP_200_OK)
    
#withoutrazorpay
class RechargeCoinsByPlanView(APIView):
    def post(self, request, user_id, plan_id):
        plan = get_object_or_404(RechargePlan, id=plan_id)
        user = get_object_or_404(User, id=user_id)

        plan_price = plan.calculate_final_price()

        user.add_coins(plan.coin_package)

        PurchaseHistory.objects.create(
            user=user,
            recharge_plan=plan,
            coins_purchased=plan.coin_package,
            purchased_price=plan_price
        )

        referral_bonus_given = False
        referral_bonus_skipped = False

        if hasattr(user, 'referred_by'): 
            referral_history = user.referred_by
            if not referral_history.recharged: 
                referral_history.recharged = True
                referral_history.save()

                referrer = referral_history.referrer
                referrer.add_coins(300)
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
            'new_coin_balance': user.coin_balance
        }, status=status.HTTP_200_OK)
    
class UserPurchaseHistoryView(APIView):
    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        purchase_history = PurchaseHistory.objects.filter(user=user)
        serializer = PurchaseHistorySerializer(purchase_history, many=True)

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

class UserStatisticsAPIView(APIView):

    def get(self, request):
        today = datetime.now().date()

        user_data = User.objects.annotate(
            total_coins_spent=Sum('caller__coins_deducted'),
            total_purchases=Count('purchasehistory'),
            total_talktime=Sum('caller__duration')
        ).values(
            'id', 'user_id', 'mobile_number', 'is_banned', 'is_online', 
            'is_suspended', 'is_dormant', 'total_coins_spent', 'total_purchases', 'total_talktime'
        )

        total_users = User.objects.count()
        active_users_count = User.objects.filter(last_login__isnull=False).count()
        inactive_users_count = total_users - active_users_count

        response_data = [
            {
                'id': user['id'],
                'User_ID': user['user_id'],
                'mobile_number': user['mobile_number'],
                'Date': today,
                'Ban': user['is_banned'],
                'Suspend': user['is_suspended'],
                'Is_Dormant': user['is_dormant'],
                'is_online': user['is_online'],
                'Total_Coin_Spend': user['total_coins_spent'] or 0,
                'Total_Purchases': user['total_purchases'] or 0,
                'Total_Talktime': user['total_talktime'] or 0,
            } for user in user_data
        ]

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
            total_purchases=Count('purchasehistory'),
            total_talktime=Sum('caller__duration')
        ).values('id', 'user_id', 'mobile_number', 'is_banned', 'is_suspended', 
                 'is_dormant', 'is_online', 'total_coins_spent', 'total_purchases', 'total_talktime').first()

        response_data = {
            'id': user_data['id'],
            'user_id': user_data['user_id'],
            'mobile_number': user_data['mobile_number'],
            'date': today,
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