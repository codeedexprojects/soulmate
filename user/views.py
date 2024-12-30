from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import *
from executive.models import *
from django.db.models import Avg
from .serializers import *
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework import generics
from datetime import datetime
from django.db.models import Sum, Count
from user.utils import send_otp_2factor
import random
from django.db.models import Count
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.db import transaction
from agora_token_builder import RtcTokenBuilder
import time
from rest_framework.exceptions import NotFound
from executive.serializers import CallRatingSerializerview
from rest_framework.generics import RetrieveAPIView

class RegisterOrLoginView(APIView):
    def post(self, request, *args, **kwargs):
        mobile_number = request.data.get('mobile_number')
        referral_code = request.data.get('referral_code')
        otp = str(random.randint(100000, 999999))  

        try:
            user = User.objects.get(mobile_number=mobile_number)

            if user.is_banned:
                return Response(
                    {'message': 'User is banned and cannot log in.', 'is_banned': True, 'is_existing_user': True},
                    status=status.HTTP_403_FORBIDDEN
                )

            try:
                send_otp_2factor(mobile_number, otp)
            except Exception as e:
                return Response(
                    {'message': 'Failed to send OTP. Please try again later.', 'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            user.otp = otp
            user.save()

            if referral_code and not hasattr(user, 'referred_by'):
                try:
                    referrer = ReferralCode.objects.get(code=referral_code).user
                    ReferralHistory.objects.create(referrer=referrer, referred_user=user)
                except ReferralCode.DoesNotExist:
                    return Response(
                        {'message': 'Invalid referral code.', 'status': False},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            return Response(
                {
                    'message': 'Login OTP sent to your mobile number.',
                    'user_id': user.id,
                    'otp': user.otp,
                    'status': True,
                    'is_existing_user': True,
                    'user_main_id': user.user_id,
                },
                status=status.HTTP_200_OK
            )

        except User.DoesNotExist:
            try:
                send_otp_2factor(mobile_number, otp)
            except Exception as e:
                return Response(
                    {'message': 'Failed to send OTP. Please try again later.', 'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            user = User.objects.create(
                mobile_number=mobile_number,
                otp=otp,
                coin_balance=300  
            )

            if referral_code:
                try:
                    referrer = ReferralCode.objects.get(code=referral_code).user
                    ReferralHistory.objects.create(referrer=referrer, referred_user=user)
                except ReferralCode.DoesNotExist:
                    return Response(
                        {'message': 'Invalid referral code.', 'status': False},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            return Response(
                {
                    'message': 'Registration OTP sent to your mobile number.',
                    'status': True,
                    'is_existing_user': False,
                    'user_id': user.id,
                    'otp': user.otp,
                    'coin_balance': user.coin_balance,
                    'user_main_id': user.user_id,
                },
                status=status.HTTP_200_OK
            )




class DeleteUserAccountView(APIView):
    def delete(self, request, user_id, *args, **kwargs):
        user = get_object_or_404(User, id=user_id)

        user.delete()

        return Response(
            {"message": f"User with ID {user_id} has been deleted successfully."},
            status=status.HTTP_200_OK
        )

class VerifyOTPView(APIView):
    def post(self, request, *args, **kwargs):
        mobile_number = request.data.get('mobile_number')
        otp = request.data.get('otp')
        name = request.data.get('name') 
        gender = request.data.get('gender')

        try:
            user = User.objects.get(mobile_number=mobile_number, otp=otp)

            is_existing_user = user.is_verified

            user.otp = None
            user.is_verified = True

            if not is_existing_user and name and gender:
                user.name = name
                user.gender = gender
                user.save()

            user.save()

            return Response(
                {
                    'message': 'OTP verified successfully.',
                    'user_id': user.id,
                    'user_main_id': user.user_id,
                    'is_existing_user': is_existing_user
                },
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {'message': 'Invalid mobile number or OTP.'},
                status=status.HTTP_400_BAD_REQUEST
            )

class GetUserCoinBalanceView(APIView):
    def get(self, request, user_id):
        user_profile = get_object_or_404(UserProfile, user_id=user_id)

        serializer = UserProfileSerializer(user_profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

class UserListView(ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserDetailView(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'id'

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.last_login = timezone.now()
        instance.save()

@api_view(['POST'])
def add_favourite(request, user_id, executive_id):
    try:
        executive = Executives.objects.get(id=executive_id)
        favourite, created = Favourite.objects.get_or_create(
            user_id=user_id,
            executive=executive
        )
        if created:
            return Response({'message': 'Favourite added successfully.'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'message': 'Already favourited'}, status=status.HTTP_400_BAD_REQUEST)
    except Executives.DoesNotExist:
        return Response({'message': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)



class ListFavouritesView(ListAPIView):
    serializer_class = FavouriteSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        return Favourite.objects.filter(user_id=user_id)


class RemoveFavouriteView(APIView):
    def delete(self, request, user_id, executive_id):
        print(f"Attempting to remove favourite for user_id: {user_id}, executive_id: {executive_id}")

        try:
            executive = Executives.objects.get(id=executive_id)
        except Executives.DoesNotExist:
            return Response({'message': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            favourite = Favourite.objects.get(user_id=user_id, executive=executive)
            favourite.delete()
            return Response({'message': 'Favourite removed successfully.'}, status=status.HTTP_200_OK)
        except Favourite.DoesNotExist:
            return Response({'message': 'Favourite not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_ratings(request, executive_id):
    try:
        executive = Executives.objects.get(id=executive_id)
        ratings = Rating.objects.filter(executive=executive)
        serializer = RatingSerializer(ratings, many=True)
        return Response(serializer.data)
    except Executives.DoesNotExist:
        return Response({'message': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def average_rating(request, executive_id):
    try:
        executive = Executives.objects.get(id=executive_id)
        average = Rating.objects.filter(executive=executive).aggregate(Avg('rating'))
        avg_rating = average['rating__avg'] or 0
        return Response({'average_rating': avg_rating}, status=status.HTTP_200_OK)
    except Executives.DoesNotExist:
        return Response({'message': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def average_rating_all_executives(request):
    executives = Executives.objects.all()
    ratings = Rating.objects.values('executive').annotate(average_rating=Avg('rating'))

    avg_ratings = {rating['executive']: rating['average_rating'] for rating in ratings}

    data = []
    for executive in executives:
        data.append({
            'id': executive.id,
            'name': executive.name,
            'average_rating': avg_ratings.get(executive.id, 0)
        })

    return Response(data, status=status.HTTP_200_OK)

def get_object_or_404(model, **kwargs):
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        raise NotFound(f"{model.__name__} not found.")


class RateExecutiveView(APIView):
    def post(self, request, user_id, executive_id):
        try:
            executive = get_object_or_404(Executives, id=executive_id)
            if Rating.objects.filter(user_id=user_id, executive=executive).exists():
                return Response({'message': 'You have already rated this executive.'}, status=status.HTTP_400_BAD_REQUEST)

            data = request.data.copy()
            data['user'] = user_id
            data['executive'] = executive_id
            serializer = RatingSerializer(data=data)

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except ValueError as ve:
            return Response({'error': str(ve)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'error': 'An unexpected error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class LogCallView(APIView):
    def get(self, request, user_id):
        executive_id = request.data.get('executive_id')
        duration = request.data.get('duration')

        user = get_object_or_404(User, id=user_id)
        executive = get_object_or_404(Executives, id=executive_id)

        call_history = AgoraCallHistory.objects.create(
            user=user,
            executive=executive,
            duration=duration,
            start_time=timezone.now()
        )
        return Response({'message': 'Call logged successfully', 'call_id': call_history.id}, status=status.HTTP_201_CREATED)

# Initiate Call API

AGORA_APP_ID = '9626e8b8b5f847e6961cb9a996e1ae93'
AGORA_APP_CERTIFICATE = 'ab41eb854807425faa1b44481ff97fe3'


@api_view(['GET'])
def call_history(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    # Sort call history by start_time in descending order
    call_history = AgoraCallHistory.objects.filter(user=user).order_by('-start_time')

    serializer = CallHistorySerializer(call_history, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)



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

import razorpay


razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


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




class UserCoinBalanceView(APIView):
    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        serializer = UserMaxCallTimeSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)



class UserProfileDetailView(APIView):
    def get(self, request, user_id):
        user_profile = get_object_or_404(UserProfile, user_id=user_id)

        serializer = UserProfileSerializer(user_profile)

        return Response(serializer.data, status=status.HTTP_200_OK)


class CarouselImageListCreateView(APIView):
    def get(self, request):
        images = CarouselImage.objects.all()
        serializer = CarouselImageSerializer(images, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CarouselImageSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CarouselImageDetailView(APIView):
    def get(self, request, image_id):
        try:
            image = CarouselImage.objects.get(id=image_id)
            serializer = CarouselImageSerializer(image)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except CarouselImage.DoesNotExist:
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, image_id):
        try:
            image = CarouselImage.objects.get(id=image_id)
            serializer = CarouselImageSerializer(image, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except CarouselImage.DoesNotExist:
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, image_id):
        try:
            image = CarouselImage.objects.get(id=image_id)
            image.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except CarouselImage.DoesNotExist:
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)


class CareerListCreateView(generics.ListCreateAPIView):
    queryset = Career.objects.all()
    serializer_class = CareerSerializer


class CareerDetailView(generics.RetrieveAPIView):
    queryset = Career.objects.all()
    serializer_class = CareerSerializer
    lookup_field = 'id'



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
    # permission_classes = [IsAuthenticated]  # Adjust permissions as needed

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

class DailyCallStatisticsView(APIView):

    def get(self, request):
        now = timezone.now()
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        intervals = [(i, i + 3) for i in range(0, 24, 3)]
        daily_stats = []

        for start_hour, end_hour in intervals:
            start_time = start_of_today + timedelta(hours=start_hour)
            end_time = start_of_today + timedelta(hours=end_hour)

            calls = AgoraCallHistory.objects.filter(start_time__gte=start_time, start_time__lt=end_time)

            total_executives = calls.values('executive').distinct().count()
            total_users = calls.values('user').distinct().count()
            total_talk_time = sum((call.end_time - call.start_time).total_seconds() / 60 for call in calls)

            daily_stats.append({
                'label': f'{start_hour:02}:00 - {end_hour:02}:00',
                'executive': total_executives,
                'user': total_users,
                'totalTalktime': total_talk_time,
            })

        return Response({'daily': daily_stats}, status=status.HTTP_200_OK)


class WeeklyCallStatisticsView(APIView):

    def get(self, request):
        now = timezone.now()
        start_of_week = now - timedelta(days=now.weekday())
        weekly_stats = []

        for i in range(7):
            current_day = start_of_week + timedelta(days=i)
            start_time = current_day.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)

            calls = AgoraCallHistory.objects.filter(start_time__gte=start_time, start_time__lt=end_time)

            total_executives = calls.values('executive').distinct().count()
            total_users = calls.values('user').distinct().count()

            total_talk_time = sum(
                (call.end_time - call.start_time).total_seconds() / 60
                for call in calls if call.start_time and call.end_time
            )

            weekly_stats.append({
                'label': current_day.strftime('%A'),
                'executive': total_executives,
                'user': total_users,
                'totalTalktime': total_talk_time,
            })

        return Response({'weekly': weekly_stats}, status=status.HTTP_200_OK)

class MonthlyCallStatisticsView(APIView):

    def get(self, request):
        now = timezone.now()
        start_of_month = now.replace(day=1)
        monthly_stats = []

        for week in range(1, 5):
            week_start = start_of_month + timedelta(weeks=week - 1)
            week_end = week_start + timedelta(weeks=1)

            calls = AgoraCallHistory.objects.filter(start_time__gte=week_start, start_time__lt=week_end)

            total_executives = calls.values('executive').distinct().count()
            total_users = calls.values('user').distinct().count()

            total_talk_time = sum(
                (call.end_time - call.start_time).total_seconds() / 60
                for call in calls if call.start_time and call.end_time
            )

            monthly_stats.append({
                'label': f'Week {week}',
                'executive': total_executives,
                'user': total_users,
                'totalTalktime': total_talk_time,
            })

        return Response({'monthly': monthly_stats}, status=status.HTTP_200_OK)



class BanUserAPIView(APIView):

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            user.is_banned = True
            user.save()
            return Response({"message": f"User {user_id} has been banned."})
        except User.DoesNotExist:
            raise NotFound("User not found")


class UnbanUserView(APIView):

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            if not user.is_banned:
                return Response({'detail': 'User is not banned.'}, status=status.HTTP_400_BAD_REQUEST)
            user.is_banned = False
            user.save()

            return Response({
                'detail': 'User has been successfully unbanned.',
                'id': user.id,
                'name': user.name,
                'mobile_number': user.mobile_number,
                'is_banned': user.is_banned
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

class SuspendUserView(APIView):

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            if user.is_suspended:
                return Response({'detail': 'User is already suspended.'}, status=status.HTTP_400_BAD_REQUEST)

            user.is_suspended = True
            user.save()

            return Response({
                'detail': 'User has been successfully suspended.',
                'id': user.id,
                'name': user.name,
                'mobile_number': user.mobile_number,
                'is_suspended': user.is_suspended
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

class UnsuspendUserView(APIView):

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            if not user.is_suspended:
                return Response({'detail': 'User is not suspended.'}, status=status.HTTP_400_BAD_REQUEST)

            user.is_suspended = False
            user.save()

            return Response({
                'detail': 'User has been successfully unsuspended.',
                'id': user.id,
                'name': user.name,
                'mobile_number': user.mobile_number,
                'is_suspended': user.is_suspended
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

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
                "final_price": str(Decimal(plan['base_price']) - (Decimal(plan['base_price']) * Decimal(plan['discount_percentage']) / Decimal(100)))
            }
            for plan in serializer.data
        ]

        return Response(response_data)




class ReferralCodeByUserView(RetrieveAPIView):
    serializer_class = ReferralCodeSerializer

    def get_object(self):
        user_id = self.kwargs.get('user_id')
        try:
            return ReferralCode.objects.get(user_id=user_id)
        except ReferralCode.DoesNotExist:
            raise NotFound("Referral code not found for the given user ID.")



class UserExecutiveRatingsView(APIView):
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise NotFound(f"User with id {user_id} does not exist.")

        ratings = CallRating.objects.filter(user=user)

        serializer = CallRatingSerializerview(ratings, many=True)
        return Response(serializer.data)

class UserExecutiveTotalRatingsView(APIView):
    def get(self, request):
        users = User.objects.all()

        user_ratings_data = []
        for user in users:
            ratings = CallRating.objects.filter(user=user)
            serializer = CallRatingSerializerview(ratings, many=True)
            user_ratings_data.append({
                "user_id": user.id,
                "ratings": serializer.data
            })

        return Response(user_ratings_data, status=200)


class CreateChannelView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        app_id = "9626e8b8b5f847e6961cb9a996e1ae93"
        app_certificate = "ab41eb854807425faa1b44481ff97fe3"
        channel_name = request.data.get("channel_name")
        executive_id = request.data.get("executive_id")
        user_id = request.data.get("user_id")
        role = 1  # Publisher (user)
        expiration_in_seconds = 3600

        # Generate unique channel name if not provided
        if not channel_name:
            channel_name = f"bestie_{uuid.uuid4().hex[:8]}_{int(time.time())}"

        # Input validation
        if not executive_id or not user_id:
            return Response({"error": "Both executive_id and user_id are required."}, status=400)

        # Validate users
        try:
            executive = Executives.objects.get(id=executive_id)
            user = User.objects.get(id=user_id)
        except Executives.DoesNotExist:
            return Response({"error": "Invalid executive_id."}, status=404)
        except User.DoesNotExist:
            return Response({"error": "Invalid user_id."}, status=404)

        # Check user's coin balance
        if user.coin_balance < 180:
            return Response({"error": "Insufficient balance. You need at least 180 coins to start a call."}, status=403)

        # Check executive's on-call status
        if executive.on_call:
            return Response({"error": "The executive is already on another call."}, status=403)
        
        if not executive.online:
            return Response({"error": "The executive is offline."}, status=403)

        # Generate Agora token for the user (publisher)
        try:
            current_time = int(time.time())
            privilege_expired_ts = current_time + expiration_in_seconds
            user_token = RtcTokenBuilder.buildTokenWithUid(
                app_id,
                app_certificate,
                channel_name,
                user.id,
                role,
                privilege_expired_ts,
            )
        except Exception as e:
            return Response({"error": f"Token generation failed: {str(e)}"}, status=500)

        # Generate Agora token for the executive (attendee)
        try:
            executive_token = RtcTokenBuilder.buildTokenWithUid(
                app_id,
                app_certificate,
                channel_name,
                executive.id,  # Executive ID as Agora UID for the attendee
                2,  # Attendee role
                privilege_expired_ts,
            )
        except Exception as e:
            return Response({"error": f"Executive token generation failed: {str(e)}"}, status=500)

        # Log the call initiation in CallHistory with pending status
        call_history = AgoraCallHistory.objects.create(
            user=user,
            executive=executive,
            channel_name=channel_name,
            executive_token=executive_token,
            token=user_token,
            start_time=now(),
            executive_joined=False,
            uid=user.id,
            status="pending",  # Set status as pending
        )

        return Response({
            "message": "Channel created successfully.",
            "token": user_token,  # User's Agora token
            "executive_token": executive_token,  # Executive's Agora token
            "channel_name": channel_name,
            "caller_name": user.name,
            "receiver_name": executive.name,
            "user_id": user.user_id,
            "executive_id": executive.executive_id,
            "executive": executive.id,
            "agora_uid": user.id,  # User's Agora UID
            "executive_agora_uid": executive.id, 
            "call_id": call_history.id  # call id from AgoraCallHistory
        }, status=200)

    

class GetRecentChannelView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, executive_id):
        try:
            # Validate executive existence
            executive = Executives.objects.get(id=executive_id)
        except Executives.DoesNotExist:
            return Response({"error": "Invalid executive_id."}, status=404)

        # Fetch the most recent call for the executive
        recent_call = AgoraCallHistory.objects.filter(
            executive=executive
        ).order_by("-start_time").first()

        if recent_call:
            # Check if the status is not "pending"
            if recent_call.status != "pending":
                return Response({"message": "No new calls."}, status=202)

            return Response({
                "message": "Channel retrieved successfully.",
                "channel_name": recent_call.channel_name,
                "call_id": recent_call.id,
                "user_id": recent_call.user.user_id,
                "gender": recent_call.user.gender,
                "executive_token": recent_call.executive_token,
                "call_status": recent_call.status,  # Get status from the model
            }, status=200)

        return Response({"message": "No recent channel found.","status":False}, status=404)


    
class ViewChannelForExecutiveView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        channel_name = request.query_params.get("channel_name")
        executive_id = request.query_params.get("executive_id")

        # Validate inputs
        if not channel_name or not executive_id:
            return Response({"error": "Channel name and executive_id are required."}, status=400)

        # Validate executive
        try:
            executive = Executives.objects.get(id=executive_id)
        except Executives.DoesNotExist:
            return Response({"error": "Executive not found."}, status=404)

        # Check if the call exists for the executive
        call_entry = AgoraCallHistory.objects.filter(
            executive=executive,
            channel_name=channel_name,
            end_time=None,
        ).first()

        if call_entry:
            # Executive already joined the channel
            return Response({
                "message": "Executive already joined the channel.",
                "channel_name": channel_name,
                "executive_name": executive.name,
                "status": "joined",
                "agora_uid": executive.id,
            }, status=200)

        return Response({
            "message": "Channel created but executive hasn't joined yet.",
            "channel_name": channel_name,
            "executive_name": executive.name,
            "status": "not_joined",
            "agora_uid": executive.id,
        }, status=200)


from threading import Timer

class JoinChannelForExecutiveView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        channel_name = request.data.get("channel_name")
        executive_id = request.data.get("executive_id")
        token = request.data.get("token")  # Executive's Agora token

        # Validate inputs
        if not channel_name or not executive_id or not token:
            return Response({"error": "Channel name, executive_id, and token are required."}, status=400)

        # Validate executive
        try:
            executive = Executives.objects.get(id=executive_id)
        except Executives.DoesNotExist:
            return Response({"error": "Executive not found."}, status=404)

        # Optionally, you can verify the token here with Agora's API (if needed).

        # Log the executive joining the channel
        call_entry = AgoraCallHistory.objects.filter(
            channel_name=channel_name, executive=executive, end_time=None).first()

        if not call_entry:
            return Response({"error": "Channel not found or already ended."}, status=404)
        
        call_entry.executive_joined = True
        call_entry.status = "joined"
        call_entry.start_time = now()
        call_entry.save()

        executive.on_call= True
        executive.save()

        return Response({
            "message": f"Executive {executive.name} successfully joined the channel.",
            "channel_name": channel_name,
            "executive_id": executive.id,
            "executive_name": executive.name,
            "status": "joined",
            "agora_uid": executive.id,
        }, status=200)











  


class GetCallStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, call_id):
        try:
            # Fetch the AgoraCallHistory entry using the provided call_id
            call_history = AgoraCallHistory.objects.get(id=call_id)
        except AgoraCallHistory.DoesNotExist:
            return Response({"error": "Invalid call_id."}, status=404)

        # Extracting the required fields from the AgoraCallHistory object
        return Response({
            "status": call_history.status,
            "executive_id": call_history.executive.id,
            "user_id": call_history.user.id,
            "gender": call_history.user.gender,
            "user":call_history.user.user_id,
            "token": call_history.token,
            "call_id": call_history.id,
            "executive_token": call_history.executive_token,
        }, status=200)
    
class LeaveChannelForExecutiveView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        call_id = request.data.get("call_id")

        # Input validation
        if not call_id:
            return Response({"error": "Call ID is required."}, status=400)

        # Validate call entry
        try:
            call_entry = AgoraCallHistory.objects.select_for_update().get(id=call_id)
        except AgoraCallHistory.DoesNotExist:
            return Response({"error": "Call history not found."}, status=404)

        # Ensure the call status is not already finalized
        if call_entry.status in ["left", "missed", "rejected"]:
            return Response({"error": f"Call already marked as {call_entry.status}."}, status=400)

        # Expire tokens when call ends or is rejected
        user = call_entry.user
        executive = call_entry.executive

        # Expiring the tokens for user and executive
        user.token_expiry = timezone.now()  # Or set to expired
        executive.token_expiry = timezone.now()  # Or set to expired
        user.save()
        executive.save()

        # Handle pending status
        if call_entry.status == "pending":
            call_entry.status = "rejected"
            call_entry.end_time = now()
            call_entry.is_active = False
            call_entry.save()

            # Set the executive's on_call status to False
            executive.on_call = False
            executive.save()

            return Response({
                "message": f"Executive {executive.name} left the channel without joining.",
                "call_id": call_entry.id,
                "status": "rejected",
            }, status=200)

        # Handle joined status
        if call_entry.status == "joined":
            call_entry.end_call()  # End the call and perform coin transfer
            call_entry.status = "left"
            call_entry.save()

            executive.on_call = False
            executive.save()

            return Response({
                "message": f"Executive {executive.name} has left the channel.",
                "call_id": call_entry.id,
                "status": "left",
                "call_duration": str(call_entry.duration),
                "coins_deducted": call_entry.coins_deducted,
                "coins_added": call_entry.coins_added,
            }, status=200)

        return Response({"error": "Unexpected call status."}, status=400)


class LeaveChannelForUserView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        call_id = request.data.get("call_id")

        # Input validation
        if not call_id:
            return Response({"error": "Call ID is required."}, status=400)

        # Validate call entry
        try:
            call_entry = AgoraCallHistory.objects.select_for_update().get(id=call_id)
        except AgoraCallHistory.DoesNotExist:
            return Response({"error": "Call history not found."}, status=404)

        # Ensure the call status is not already finalized
        if call_entry.status in ["left", "missed", "rejected"]:
            return Response({"error": f"Call already marked as {call_entry.status}."}, status=400)

        # Expire tokens when call ends or is missed
        user = call_entry.user
        executive = call_entry.executive

        # Expiring the tokens for user and executive
        user.token_expiry = timezone.now()  # Or set to expired
        executive.token_expiry = timezone.now()  # Or set to expired
        user.save()
        executive.save()

        # Handle pending status
        if call_entry.status == "pending":
            call_entry.status="missed"  # Mark as missed if the executive did not join
            call_entry.save()

            return Response({
                "message": f"Call was missed without joining.",
                "call_id": call_entry.id,
                "status": "missed",
            }, status=200)

        # Handle joined status
        if call_entry.status == "joined":
            call_entry.end_call()  # End the call and perform coin transfer
            call_entry.status = "left"
            call_entry.save()
        
            executive.on_call = False
            executive.save()

            return Response({
                "message": "Call ended successfully.",
                "call_id": call_entry.id,
                "status": "left",
                "call_duration": str(call_entry.duration),
                "coins_deducted": call_entry.coins_deducted,
                "coins_added": call_entry.coins_added,
            }, status=200)

        return Response({"error": "Unexpected call status."}, status=400)
        
class LeaveAllCallsForExecutiveView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        executive_id = request.data.get("executive_id")

        # Validate input
        if not executive_id:
            return Response({"error": "Executive ID is required."}, status=400)

        # Validate executive
        try:
            executive = Executives.objects.get(id=executive_id)
        except Executives.DoesNotExist:
            return Response({"error": "Executive not found."}, status=404)

        # Fetch all ongoing calls (both pending and joined)
        ongoing_calls = AgoraCallHistory.objects.filter(executive=executive, end_time=None)

        if not ongoing_calls.exists():
            return Response({"message": "No ongoing calls found for this executive."}, status=404)

        # Expire tokens for the executive
        executive.token_expiry = timezone.now()  # Or set to expired
        executive.save()

        for call_entry in ongoing_calls:
            if call_entry.status == "pending":
                # Mark pending calls as missed
                call_entry.status = "missed"
                call_entry.end_time = now()
                call_entry.save()

            elif call_entry.status == "joined":
                # Mark joined calls as left
                call_entry.status = "left"
                call_entry.end_time = now()
                call_duration = call_entry.end_time - call_entry.start_time
                call_entry.duration = call_duration

                # Deduct coins from user and add to executive
                user = call_entry.user
                total_seconds = int(call_duration.total_seconds())
                coins_to_deduct = total_seconds * 3  # 3 coins per second

                if user.coin_balance < coins_to_deduct:
                    coins_to_deduct = user.coin_balance  # Adjust if user has insufficient coins

                user.coin_balance -= coins_to_deduct
                executive.coins_balance += coins_to_deduct
                user.save()
                executive.save()

                # Save the coin deduction details
                call_entry.coins_deducted = coins_to_deduct
                call_entry.coins_added = coins_to_deduct
                call_entry.save()

        # Set the executive's on_call status to False
        executive.on_call = False
        executive.save()

        return Response({
            "message": f"All ongoing calls for executive {executive.name} have been ended.",
            "executive_name": executive.name,
            "executive_id": executive.id,
        }, status=200)

class BlockUserAPIView(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        executive_id = request.data.get('executive_id')
        reason = request.data.get('reason')

        # Ensure both user_id and executive_id are provided, and reason is present
        if not user_id or not executive_id:
            return Response({'error': 'User ID and Executive ID are required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not reason:
            return Response({'error': 'Reason is required to block the user.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create or update block entry with is_blocked set to True and the provided reason
        block_entry, created = UserBlock.objects.update_or_create(
            user_id=user_id,
            executive_id=executive_id,
            defaults={
                'is_blocked': True,
                'reason': reason
            }
        )

        message = 'User has been blocked successfully.'
        return Response({'message': message}, status=status.HTTP_200_OK)

class UnblockUserAPIView(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        executive_id = request.data.get('executive_id')

        # Ensure both user_id and executive_id are provided
        if not user_id or not executive_id:
            return Response({'error': 'User ID and Executive ID are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create or update block entry with is_blocked set to False
        block_entry, created = UserBlock.objects.update_or_create(
            user_id=user_id,
            executive_id=executive_id,
            defaults={
                'is_blocked': False,
                'reason': ''  # No reason provided when unblocking
            }
        )

        message = 'User has been unblocked successfully.'
        return Response({'message': message}, status=status.HTTP_200_OK)



class BlockedUsersListAPIView(APIView):
    def get(self, request, executive_id):
        blocked_users = UserBlock.objects.filter(is_blocked=True, executive_id=executive_id)
        serializer = UserBlockListSerializer(blocked_users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
