from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import *
from executive.models import *
from django.db.models import Avg
from .serializers import *
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView, UpdateAPIView
from rest_framework.generics import ListAPIView
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework import generics
from datetime import datetime
from django.db.models import Sum, Count, Q
from user.utils import send_otp_2factor
import random
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict


class RegisterOrLoginView(APIView):
    def post(self, request, *args, **kwargs):
        mobile_number = request.data.get('mobile_number')
        otp = str(random.randint(100000, 999999))  # Generate OTP

        try:
            # Check if user already exists
            user = User.objects.get(mobile_number=mobile_number)

            if user.is_banned:
                return Response(
                    {'message': 'User is banned and cannot log in.', 'is_banned': True, 'is_existing_user': True},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Send OTP for existing user
            try:
                send_otp_2factor(mobile_number, otp)
            except Exception as e:
                return Response(
                    {'message': 'Failed to send OTP. Please try again later.', 'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Update OTP for the user
            user.otp = otp
            user.save()

            return Response(
                {
                    'message': 'Login OTP sent to your mobile number.',
                    'user_id': user.id,
                    'otp': user.otp,
                    'status': True,
                    'is_existing_user': True
                },
                status=status.HTTP_200_OK
            )

        except User.DoesNotExist:
            # Handle new user registration
            try:
                send_otp_2factor(mobile_number, otp)
            except Exception as e:
                return Response(
                    {'message': 'Failed to send OTP. Please try again later.', 'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Create a new user with default coin balance
            user = User.objects.create(
                mobile_number=mobile_number,
                otp=otp,
                coin_balance=300  # Default coin balance for new user
            )

            return Response(
                {
                    'message': 'Registration OTP sent to your mobile number.',
                    'status': True,
                    'is_existing_user': False,
                    'user_id': user.id,
                    'otp': user.otp,
                    'coin_balance': user.coin_balance
                },
                status=status.HTTP_200_OK
            )



class VerifyOTPView(APIView):
    def post(self, request, *args, **kwargs):
        mobile_number = request.data.get('mobile_number')
        otp = request.data.get('otp')
        name = request.data.get('name')  # Collect additional user details for registration
        gender = request.data.get('gender')

        try:
            # Fetch the user based on mobile_number and otp
            user = User.objects.get(mobile_number=mobile_number, otp=otp)

            # Check if the user was already verified before OTP verification
            is_existing_user = user.is_verified

            # Update the user's verification status
            user.otp = None
            user.is_verified = True

            # If the user is new, save additional details
            if not is_existing_user and name and gender:
                user.name = name
                user.gender = gender
                user.save()

            user.save()

            return Response(
                {
                    'message': 'OTP verified successfully.',
                    'user_id': user.id,
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

from rest_framework.permissions import AllowAny


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

from rest_framework.exceptions import NotFound


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

        call_history = CallHistory.objects.create(
            user=user,
            executive=executive,
            duration=duration,
            start_time=timezone.now()
        )
        return Response({'message': 'Call logged successfully', 'call_id': call_history.id}, status=status.HTTP_201_CREATED)




from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
import requests


# Initiate Call API
class InitiateCallView(APIView):
    def post(self, request, user_id, executive_id):
        zegocloud_call_id = request.data.get('zegocloud_call_id')

        if not zegocloud_call_id:
            return Response({'error': 'ZEGOCLOUD call ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
            executive = Executives.objects.get(id=executive_id)
        except (User.DoesNotExist, Executives.DoesNotExist):
            return Response({'error': 'User or Executive not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if the executive is already on a call
        if executive.on_call:
            return Response({'error': 'Executive is on another call, please try again later'}, status=status.HTTP_400_BAD_REQUEST)

        coins_per_second = Decimal(executive.coins_per_second)
        if user.coin_balance < coins_per_second:
            return Response({'error': 'Insufficient coins'}, status=status.HTTP_400_BAD_REQUEST)

        # Create the user call history record
        user_call_history = CallHistory.objects.create(
            user=user,
            executive=executive,
            start_time=timezone.now(),
            status='initiated',
            zegocloud_call_id=zegocloud_call_id
        )

        # Create the executive call history record
        executive_call_history = ExecutiveCallHistory.objects.create(
            executive=executive,
            user=user,
            call_history=user_call_history,
            start_time=timezone.now(),
            status='initiated',
            zegocloud_call_id=zegocloud_call_id
        )

        # Check if the call has been initiated for more than 60 seconds and mark as missed
        self.check_call_timeout(user_call_history)

        return Response({
            'message': 'Call initiated successfully',
            'user_call_history_id': user_call_history.id,
            'executive_call_history_id': executive_call_history.id,
            'status': user_call_history.status,
            'zegocloud_call_id': zegocloud_call_id
        }, status=status.HTTP_201_CREATED)

    def check_call_timeout(self, call_history):
        # Check if the call is still in 'initiated' status after 60 seconds
        if call_history.status == 'initiated':
            time_diff = timezone.now() - call_history.start_time
            if time_diff > timedelta(seconds=60):  # More than 60 seconds
                call_history.status = 'missed'
                call_history.save()
                # Also update the executive's call history to 'missed'
                executive_call_history = ExecutiveCallHistory.objects.get(call_history=call_history)
                executive_call_history.status = 'missed'
                executive_call_history.save()


# class InitiateCallView(APIView):
#     def post(self, request, user_id, executive_id):
#         zegocloud_call_id = request.data.get('zegocloud_call_id')  # Optional field

#         try:
#             user = User.objects.get(id=user_id)
#             executive = Executives.objects.get(id=executive_id)
#         except (User.DoesNotExist, Executives.DoesNotExist):
#             return Response({'error': 'User or Executive not found'}, status=status.HTTP_404_NOT_FOUND)

#         coins_per_second = Decimal(executive.coins_per_second)
#         if user.coin_balance < coins_per_second:
#             return Response({'error': 'Insufficient coins'}, status=status.HTTP_400_BAD_REQUEST)

#         # Create user call history
#         user_call_history = CallHistory.objects.create(
#             user=user,
#             executive=executive,
#             start_time=timezone.now(),
#             status='initiated',
#             zegocloud_call_id=zegocloud_call_id  # May be None
#         )

#         # Create executive call history
#         executive_call_history = ExecutiveCallHistory.objects.create(
#             executive=executive,
#             user=user,
#             call_history=user_call_history,
#             start_time=timezone.now(),
#             status='initiated',
#             zegocloud_call_id=zegocloud_call_id  # May be None
#         )

#         # Check if the call remains initiated for more than 60 seconds and mark as missed
#         self.check_call_timeout(user_call_history)

#         return Response({
#             'message': 'Call initiated successfully',
#             'user_call_history_id': user_call_history.id,
#             'executive_call_history_id': executive_call_history.id,
#             'status': user_call_history.status,
#             'zegocloud_call_id': zegocloud_call_id
#         }, status=status.HTTP_201_CREATED)

#     def check_call_timeout(self, call_history):
#         # This method can be invoked asynchronously or managed via Celery to check after 60 seconds
#         if call_history.status == 'initiated':
#             time_diff = timezone.now() - call_history.start_time
#             if time_diff > timedelta(seconds=45):  # More than 60 seconds
#                 call_history.status = 'missed'
#                 call_history.save()
#                 # Update executive's call history to 'missed'
#                 executive_call_history = ExecutiveCallHistory.objects.get(call_history=call_history)
#                 executive_call_history.status = 'missed'
#                 executive_call_history.save()


class EndCallView(APIView):
    def post(self, request, zegocloud_call_id):
        call_history = get_object_or_404(CallHistory, zegocloud_call_id=zegocloud_call_id)

        if call_history.end_time:
            return Response({'error': 'Call has already ended'}, status=status.HTTP_400_BAD_REQUEST)

        user = call_history.user
        executive = call_history.executive

        # Determine status based on the current state
        if call_history.status == 'initiated':
            call_history.status = 'missed'
            executive_call_history = get_object_or_404(ExecutiveCallHistory, call_history=call_history)
            executive_call_history.status = 'missed'
            executive_call_history.save()
            coins_deducted = 0
        elif call_history.status == 'accepted':
            call_history.status = 'ended'
            call_history.end_time = timezone.now()

            # Calculate call duration
            total_duration_seconds = (call_history.end_time - call_history.start_time).total_seconds()
            coins_per_second = Decimal(executive.coins_per_second)
            coins_deducted = (Decimal(total_duration_seconds) / Decimal(60)) * coins_per_second

            # Deduct coins from the user and add to the executive
            user.coin_balance -= coins_deducted
            user.save()

            executive.coins_balance += coins_deducted
            executive.save()

            # Log talk time for the call
            TalkTime.objects.create(
                call_history=call_history,
                executive=executive,
                duration=call_history.end_time - call_history.start_time,
                coins_deducted=coins_deducted
            )
        else:
            return Response({'error': 'Invalid call status'}, status=status.HTTP_400_BAD_REQUEST)

        # Reset the executive's "on_call" status
        executive.on_call = False
        executive.save()

        # Save call history
        call_history.save()

        # Prepare response
        duration = "0h 0m 0s"
        if call_history.status == 'ended':
            hours, remainder = divmod(total_duration_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

        response_data = {
            'message': 'Call ended successfully',
            'call_id': call_history.id,
            'duration': duration,
            'coins_deducted': float(coins_deducted),
            'executive_balance_after_call': float(executive.coins_balance),
            'user_balance_after_call': float(user.coin_balance),
            'user_id': user.id,
            'executive_id': executive.id,
            'call_accepted_time': call_history.start_time,
            'call_end_time': call_history.end_time,
            'status': call_history.status
        }

        return Response(response_data, status=status.HTTP_200_OK)



@api_view(['GET'])
def call_history(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    # Sort call history by start_time in descending order
    call_history = CallHistory.objects.filter(user=user).order_by('-start_time')

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

        user.add_coins(plan.coin_package)

        PurchaseHistory.objects.create(
            user=user,
            recharge_plan=plan,
            coins_purchased=plan.coin_package

        )

        plan_serializer = RechargePlanSerializer(plan)

        return Response({
            'message': 'Coins recharged successfully.',
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

        logged_in_today = User.objects.filter(last_login__date=today).count()

        total_executives_on_call = ExecutiveCallHistory.objects.filter(status='accepted', end_time__isnull=True).count()

        total_talk_duration = CallHistory.objects.filter(
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
            total_coins_spent=Sum('purchasehistory__purchased_price'),
            total_purchases=Count('purchasehistory'),
            total_talktime=Sum('callhistory__duration')
        ).values(
            'id', 'user_id','mobile_number','is_banned','is_online','is_suspended','is_dormant','total_coins_spent', 'total_purchases', 'total_talktime'
        )

        total_users = User.objects.count()
        active_users_count = User.objects.filter(last_login__isnull=False).count()
        inactive_users_count = total_users - active_users_count

        response_data = [
            {
                'id': user['id'],
                'User_ID': user['user_id'],
                'mobile_number':user['mobile_number'],
                'Date': today,
                'Ban':user['is_banned'],
                'Suspend':user['is_suspended'],
                'Is_Dormant':user['is_dormant'],
                'is_online':user['is_online'],
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

        total_coins_spent = PurchaseHistory.objects.filter(user=user).aggregate(
            total_spent=Sum('purchased_price')
        )['total_spent'] or 0

        total_purchases = PurchaseHistory.objects.filter(user=user).count()
        total_talktime = CallHistory.objects.filter(user=user).aggregate(
            total_duration=Sum('duration')
        )['total_duration'] or 0

        response_data = {
            'User_ID': user.id,  
            'Date': today,
            'Total_Coin_Spent': total_coins_spent,
            'Total_Purchases': total_purchases,
            'Total_Talktime': total_talktime,
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

            calls = CallHistory.objects.filter(start_time__gte=start_time, start_time__lt=end_time)

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

            calls = CallHistory.objects.filter(start_time__gte=start_time, start_time__lt=end_time)

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

            calls = CallHistory.objects.filter(start_time__gte=week_start, start_time__lt=week_end)

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