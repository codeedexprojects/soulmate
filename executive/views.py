from .serializers import *
from user.serializers import *

from rest_framework import generics
from .models import *
from user.models import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.exceptions import NotFound
from django.shortcuts import get_object_or_404
from datetime import timedelta
from django.contrib.auth import logout
from django.db.models.functions import Coalesce
from django.db.models import Sum, F
from rest_framework.decorators import action
from .utils import send_otp, generate_otp
from rest_framework.permissions import AllowAny

#OTPAUTH
class ExeRegisterOrLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        mobile_number = request.data.get('mobile_number')
        otp = generate_otp() 

        try:
            executive = Executives.objects.get(mobile_number=mobile_number)

            if executive.is_banned:
                return Response({'message': 'Executive is banned and cannot log in.', 'is_banned': True},
                                status=status.HTTP_403_FORBIDDEN)

            if send_otp(mobile_number, otp):
                executive.otp = otp
                executive.save()
                return Response({
                    'message': 'Login OTP sent to your mobile number.',
                    'executive_id': executive.id,
                    'status': True,
                    'is_suspended': executive.is_suspended
                }, status=status.HTTP_200_OK)
            else:
                return Response({'message': 'Failed to send OTP. Please try again later.'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Executives.DoesNotExist:
            serializer = ExecutivesSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            if send_otp(mobile_number, otp):
                executive = serializer.save(otp=otp)
                return Response({
                    'message': 'Executive registered successfully. OTP sent to your mobile number.',
                    'executive_id': executive.id,
                    'status': True,
                    'is_suspended': False
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({'message': 'Failed to send OTP. Please try again later.'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExeVerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        mobile_number = request.data.get('mobile_number')
        otp = request.data.get('otp')

        try:
            executive = Executives.objects.get(mobile_number=mobile_number, otp=otp)
            executive.otp = None
            executive.is_verified = True
            executive.save()
            return Response({'message': 'OTP verified successfully.', 'executive_id': executive.id},
                            status=status.HTTP_200_OK)
        except Executives.DoesNotExist:
            return Response({'message': 'Invalid mobile number or OTP.'},
                            status=status.HTTP_400_BAD_REQUEST)

#Authentication
class RegisterExecutiveView(generics.CreateAPIView):
    queryset = Executives.objects.all()
    serializer_class = ExecutivesSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class ExecutiveLoginView(APIView):
    def post(self, request):
        serializer = ExecutiveLoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#Listing

class ListExecutivesView(generics.ListAPIView):
    queryset = Executives.objects.all()
    serializer_class = ExecutivesSerializer

class ListExecutivesByUserView(generics.ListAPIView):
    serializer_class = ExecutivesSerializer

    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        if not user_id:
            raise NotFound("User ID is required.")
        
        return Executives.objects.filter(
            is_suspended=False, 
            is_banned=False
        ).order_by('-online') 

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['user_id'] = self.kwargs['user_id']
        context['request'] = self.request
        return context


class UserCallDurationView(APIView):
    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)

        executives = Executives.objects.all()

        serializer = ExecutivesSerializer(executives, many=True, context={'user': user})

        return Response({
            'user_coin_balance': user.coin_balance, 
            'executives': serializer.data  
        }, status=status.HTTP_200_OK)


class ExecutiveDetailView(APIView):
    def get(self, request, pk):
        executive = get_object_or_404(Executives, pk=pk)
        serializer = ExecutivesSerializer(executive)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        executive = get_object_or_404(Executives, pk=pk)
        serializer = ExecutivesSerializer(executive, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        executive = get_object_or_404(Executives, pk=pk)
        serializer = ExecutivesSerializer(executive, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        executive = get_object_or_404(Executives, pk=pk)
        executive.delete()
        return Response({'message': 'Executive deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


class SetOnlineView(APIView):
    def patch(self, request, pk):
        try:
            executive = Executives.objects.get(id=pk)
            executive.online = True
            executive.save()

            serializer = ExecutivesSerializer(executive, context={'user_id': request.user.id})
            return Response({
                'message': 'Executive is now online.',
                'details': serializer.data
            }, status=status.HTTP_200_OK)

        except Executives.DoesNotExist:
            return Response({'message': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)

class SetOfflineView(APIView):
    def patch(self, request, pk):
        try:
            executive = Executives.objects.get(id=pk)
            executive.online = False
            executive.save()

            serializer = ExecutivesSerializer(executive, context={'user_id': request.user.id})
            return Response({
                'message': 'Executive is now offline.',
                'details': serializer.data
            }, status=status.HTTP_200_OK)

        except Executives.DoesNotExist:
            return Response({'message': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)



class ExecutiveStatusView(APIView):
    def get(self, request, executive_id):
        executive = Executives.objects.get(id=executive_id)

        total_on_duty = str(timedelta(seconds=executive.total_on_duty_seconds))

        if executive.online and executive.duty_start_time:
            current_session_duration = timezone.now() - executive.duty_start_time
            total_on_duty = str(timedelta(seconds=executive.total_on_duty_seconds + current_session_duration.total_seconds()))

        total_talk_time_today = str(timedelta(seconds=executive.total_talk_seconds_today))

        return Response({
            'id': executive.id,
            'executive_name': executive.name,
            'total_on_duty_time': total_on_duty,
            'total_talk_time_today': total_talk_time_today,
            'total_picked_calls': executive.total_picked_calls,
            'total_missed_calls': executive.total_missed_calls,
            'online': executive.online
        }, status=status.HTTP_200_OK)

from .tasks import deduct_coins

class AcceptCallView(APIView):
    def post(self, request, zegocloud_call_id):
        try:
            call_history = CallHistory.objects.get(zegocloud_call_id=zegocloud_call_id)
        except CallHistory.DoesNotExist:
            return Response({'error': 'Call history not found'}, status=status.HTTP_404_NOT_FOUND)

        # Set the call status to 'accepted'
        call_history.status = 'accepted'
        call_history.save()

        # Trigger the Celery task for coin deduction
        deduct_coins.delay(call_history.id)

        return Response({'message': 'Call accepted and task queued.'})




# from .tasks import deduct_coins_periodically



# class AcceptCallView(APIView):
#     def post(self, request, zegocloud_call_id):
#         try:
#             # Fetch call history records
#             user_call_history = CallHistory.objects.get(zegocloud_call_id=zegocloud_call_id)
#             executive_call_history = ExecutiveCallHistory.objects.get(call_history=user_call_history)
#         except CallHistory.DoesNotExist:
#             return Response({'error': 'User CallHistory not found'}, status=status.HTTP_404_NOT_FOUND)
#         except ExecutiveCallHistory.DoesNotExist:
#             return Response({'error': 'Executive CallHistory not found'}, status=status.HTTP_404_NOT_FOUND)

#         # Ensure the call is in the 'initiated' state
#         if user_call_history.status != 'initiated':
#             return Response(
#                 {'error': 'Call has already been accepted or is not in initiated state'}, 
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         user = user_call_history.user
#         executive = user_call_history.executive

#         # Check if the executive is already on a call
#         if executive.on_call:
#             active_calls = CallHistory.objects.filter(executive=executive, status='accepted').exists()
#             if not active_calls:
#                 executive.on_call = False  # Reset if no active calls are found
#                 executive.save()
#             else:
#                 return Response({'error': 'Executive is already on a call'}, status=status.HTTP_400_BAD_REQUEST)

#         coins_per_second = Decimal(executive.coins_per_second)

#         # Validate the coins-per-second rate
#         if coins_per_second <= 0:
#             return Response(
#                 {'error': 'Executive coin rate per second is set to zero, cannot proceed with call'}, 
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         # Ensure the user has enough coins to accept the call
#         if user.coin_balance < coins_per_second:
#             return Response({'error': 'Insufficient coins to accept call'}, status=status.HTTP_400_BAD_REQUEST)

#         # Deduct initial coins from user and update balances
#         user.coin_balance -= coins_per_second
#         user.save()

#         executive.coins_balance += coins_per_second
#         executive.on_call = True  # Mark the executive as on a call
#         executive.save()

#         # Update call histories
#         user_call_history.status = 'accepted'
#         user_call_history.start_time = timezone.now()
#         user_call_history.save()

#         executive_call_history.status = 'accepted'
#         executive_call_history.start_time = timezone.now()
#         executive_call_history.save()

#         deduct_coins_periodically.apply_async((user_call_history.id,), countdown=1)

#         return Response({
#             'message': 'Call accepted successfully.',
#             'user_call_history_id': user_call_history.id,
#             'executive_call_history_id': executive_call_history.id,
#             'status': user_call_history.status,
#             'initial_deduction': float(coins_per_second),
#             'user_balance_after_deduction': float(user.coin_balance),
#             'executive_balance_after_deduction': float(executive.coins_balance),
#         }, status=status.HTTP_200_OK)

#     def end_call(self, user_call_history, executive_call_history, user, executive):
#         # Calculate the total call duration in seconds
#         call_duration = user_call_history.end_time - user_call_history.start_time
#         call_duration_seconds = int(call_duration.total_seconds())

#         # Deduct coins from the user at a fixed rate of 3 coins per second
#         total_deduction = 3 * call_duration_seconds  # Fixed deduction rate: 3 coins per second

#         # Deduct coins from user and add to executive's balance
#         user.coin_balance -= total_deduction
#         executive.coins_balance += total_deduction

#         # Update the user's and executive's balances
#         user.save()
#         executive.save()

#         # Change the status to 'ended'
#         user_call_history.status = 'ended'
#         user_call_history.end_time = timezone.now()
#         user_call_history.save()

#         executive_call_history.status = 'ended'
#         executive_call_history.end_time = timezone.now()
#         executive_call_history.save()

#         # Reset executive's on-call status
#         executive.on_call = False
#         executive.save()

#         return Response({
#             'message': 'Call ended successfully.',
#             'user_call_history_id': user_call_history.id,
#             'executive_call_history_id': executive_call_history.id,
#             'status': user_call_history.status,
#             'user_balance': float(user.coin_balance),
#             'executive_balance': float(executive.coins_balance),
#         }, status=status.HTTP_200_OK)

#     def check_and_end_call(self, user_call_history, executive_call_history, user, executive):
#         # Check if the user coin balance is below threshold
#         if user.coin_balance < 3:
#             self.end_call(user_call_history, executive_call_history, user, executive)



# import time
# from threading import Thread

# class AcceptCallView(APIView):
#     def post(self, request, zegocloud_call_id):
#         try:
#             # Fetch call history records
#             user_call_history = CallHistory.objects.get(zegocloud_call_id=zegocloud_call_id)
#             executive_call_history = ExecutiveCallHistory.objects.get(call_history=user_call_history)
#         except CallHistory.DoesNotExist:
#             return Response({'error': 'User CallHistory not found'}, status=status.HTTP_404_NOT_FOUND)
#         except ExecutiveCallHistory.DoesNotExist:
#             return Response({'error': 'Executive CallHistory not found'}, status=status.HTTP_404_NOT_FOUND)

#         # Ensure the call is in the 'initiated' state
#         if user_call_history.status != 'initiated':
#             return Response(
#                 {'error': 'Call has already been accepted or is not in initiated state'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         user = user_call_history.user
#         executive = user_call_history.executive

#         # Check if the executive is already on a call
#         if executive.on_call:
#             active_calls = CallHistory.objects.filter(executive=executive, status='accepted').exists()
#             if not active_calls:
#                 executive.on_call = False  # Reset if no active calls are found
#                 executive.save()
#             else:
#                 return Response({'error': 'Executive is already on a call'}, status=status.HTTP_400_BAD_REQUEST)

#         # Validate coins-per-second rate
#         coins_per_second = Decimal(executive.coins_per_second)
#         if coins_per_second <= 0:
#             return Response(
#                 {'error': 'Executive coin rate per second is set to zero, cannot proceed with call'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         # Ensure the user has enough coins to accept the call
#         if user.coin_balance < coins_per_second:
#             return Response({'error': 'Insufficient coins to accept call'}, status=status.HTTP_400_BAD_REQUEST)

#         # Deduct initial coins
#         user.coin_balance -= coins_per_second
#         user.save()

#         executive.coins_balance += coins_per_second
#         executive.on_call = True
#         executive.save()

#         # Update call histories
#         user_call_history.status = 'accepted'
#         user_call_history.start_time = timezone.now()
#         user_call_history.save()

#         executive_call_history.status = 'accepted'
#         executive_call_history.start_time = timezone.now()
#         executive_call_history.save()

#         # Start the coin deduction loop in a separate thread
#         Thread(target=self.deduct_coins_in_real_time, args=(user_call_history, executive_call_history, user, executive)).start()

#         return Response({
#             'message': 'Call accepted successfully.',
#             'user_call_history_id': user_call_history.id,
#             'executive_call_history_id': executive_call_history.id,
#             'status': user_call_history.status,
#             'initial_deduction': float(coins_per_second),
#             'user_balance_after_deduction': float(user.coin_balance),
#             'executive_balance_after_deduction': float(executive.coins_balance),
#         }, status=status.HTTP_200_OK)

#     def deduct_coins_in_real_time(self, user_call_history, executive_call_history, user, executive):
#         coins_per_second = Decimal(executive.coins_per_second)

#         while True:
#             # Check if the call is still active
#             if user_call_history.status != 'accepted':
#                 break

#             # Check if the user has enough coins to continue the call
#             if user.coin_balance < coins_per_second:
#                 # End the call if the user runs out of coins
#                 self.end_call(user_call_history, executive_call_history, user, executive)
#                 break

#             # Deduct coins from the user and add to the executive's balance
#             user.coin_balance -= coins_per_second
#             executive.coins_balance += coins_per_second

#             user.save()
#             executive.save()

#             # Wait for 1 second
#             time.sleep(1)

#     def end_call(self, user_call_history, executive_call_history, user, executive):
#         # End the call by updating call history and executive status
#         user_call_history.end_time = timezone.now()
#         user_call_history.status = 'ended'
#         user_call_history.save()

#         executive_call_history.end_time = timezone.now()
#         executive_call_history.status = 'ended'
#         executive_call_history.save()

#         executive.on_call = False
#         executive.save()



class ExeCallHistoryListView(generics.ListAPIView):
    serializer_class = ExeCallHistorySerializer

    def get_queryset(self):
        executive_id = self.kwargs['executive_id']
        return CallHistory.objects.filter(executive_id=executive_id)


class CreateAdminView(generics.CreateAPIView):
    queryset = Admins.objects.all()
    serializer_class = AdminSerializer

    def perform_create(self, serializer):
        serializer.save()



class ListAdminView(generics.ListAPIView):
    queryset = Admins.objects.all()
    serializer_class = AdminSerializer

class SuperuserLoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get the admin instance from validated data
        admin = serializer.validated_data['admin']
        
        return Response({
            'message': 'Login successful',
            'email': admin.email,
            'name': admin.name,
            'role': admin.role,
            'id': admin.id
        }, status=status.HTTP_200_OK)

class AdminLogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)


#banorsuspend

class BanExecutiveAPIView(APIView):

    def post(self, request, executive_id):
        try:
            executive = Executives.objects.get(executive_id=executive_id)
            executive.is_banned = True
            executive.save()
            return Response({"message": f"Executive {executive_id} has been banned."})
        except Executives.DoesNotExist:
            raise NotFound("Executive not found")


class UnbanExecutiveView(APIView):

    def post(self, request, executive_id):
        try:
            executive = Executives.objects.get(executive_id=executive_id)
            if not executive.is_banned:
                return Response({'detail': 'Executive is not banned.'}, status=status.HTTP_400_BAD_REQUEST)
            executive.is_banned = False
            executive.save()

            return Response({
                'detail': 'Executive has been successfully unbanned.',
                'id': executive.id,
                'name': executive.name,
                'mobile_number': executive.mobile_number,
                'is_banned': executive.is_banned
            }, status=status.HTTP_200_OK)

        except Executives.DoesNotExist:
            return Response({'detail': 'Executive not found.'}, status=status.HTTP_404_NOT_FOUND)

class SuspendExecutiveView(APIView):

    def post(self, request, executive_id):
        try:
            executive = Executives.objects.get(id=executive_id)
            if executive.is_suspended:
                return Response({'detail': 'Executive is already suspended.'}, status=status.HTTP_400_BAD_REQUEST)

            executive.is_suspended = True
            executive.save()

            return Response({
                'detail': 'Executive has been successfully suspended.',
                'id': executive.id,
                'name': executive.name,
                'mobile_number': executive.mobile_number,
                'is_suspended': executive.is_suspended
            }, status=status.HTTP_200_OK)

        except Executives.DoesNotExist:
            return Response({'detail': 'Executive not found.'}, status=status.HTTP_404_NOT_FOUND)

class UnsuspendExecutiveView(APIView):

    def post(self, request, executive_id):
        try:
            executive = Executives.objects.get(id=executive_id)
            if not executive.is_suspended:
                return Response({'detail': 'Executive is not suspended.'}, status=status.HTTP_400_BAD_REQUEST)

            executive.is_suspended = False
            executive.save()

            return Response({
                'detail': 'Executive has been successfully unsuspended.',
                'id': executive.id,
                'name': executive.name,
                'mobile_number': executive.mobile_number,
                'is_suspended': executive.is_suspended
            }, status=status.HTTP_200_OK)

        except Executives.DoesNotExist:
            return Response({'detail': 'Executive not found.'}, status=status.HTTP_404_NOT_FOUND)

class CallHistoryViewSet(viewsets.ModelViewSet):
    queryset = ExecutiveCallHistory.objects.all()
    serializer_class = CallHistoryRatingSerializer
    # permission_classes = [IsAuthenticated]  

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()  

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True) 

        self.perform_update(serializer)  

        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()  
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ExecutiveCoinBalanceView(APIView):
    def get(self, request, executive_id):
        executive = get_object_or_404(Executives, id=executive_id)

        response_data = {
            'executive_id': executive.id,
            'name': executive.name,
            'coin_balance': str(executive.coins_balance),  
            'mobile_number': executive.mobile_number,
            'email_id': executive.email_id,
            'profession': executive.profession,
        }

        return Response(response_data, status=status.HTTP_200_OK)

class CoinRedemptionRequestView(APIView):
    
    def post(self, request, executive_id, coin_conversion_id):
        executive = get_object_or_404(Executives, id=executive_id)
        coin_conversion = get_object_or_404(CoinConversion, id=coin_conversion_id)

        if executive.coins_balance < coin_conversion.coins_earned:
            return Response(
                {'error': 'Insufficient coin balance to withdraw'},
                status=status.HTTP_400_BAD_REQUEST
            )

        executive.coins_balance -= coin_conversion.coins_earned
        executive.save()

        redemption_request = CoinRedemptionRequest.objects.create(
            executive=executive,
            coin_conversion=coin_conversion,
            amount_requested=coin_conversion.rupees,
        )

        return Response({
            'message': 'Redemption request created successfully',
            'request_id': redemption_request.id,
            'amount_requested': float(redemption_request.amount_requested),
            'status': redemption_request.status
        }, status=status.HTTP_201_CREATED)

    def get(self, request, executive_id=None):
        if executive_id:
            executive = get_object_or_404(Executives, id=executive_id)
            redemption_requests = CoinRedemptionRequest.objects.filter(executive=executive)
        else:
            redemption_requests = CoinRedemptionRequest.objects.all()

        serializer = CoinRedemptionRequestSerializer(redemption_requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class RedemptionRequestListView(generics.ListAPIView):
    queryset = CoinRedemptionRequest.objects.all()
    serializer_class = CoinRedemptionRequestSerializer 

    def get(self, request):
        redemption_requests = self.get_queryset()
        serializer = self.get_serializer(redemption_requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ExecutiveCallHistoryListView(APIView):
    def get(self, request, executive_id):
        # Fetch the executive object
        executive = get_object_or_404(Executives, id=executive_id)
        
        # Filter call histories associated with the executive
        call_histories = ExecutiveCallHistory.objects.filter(executive=executive)
        
        # Serialize the data using CallHistorySerializer
        serializer = CallHistorySerializer(call_histories, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)


from rest_framework.generics import RetrieveUpdateDestroyAPIView

class RevenueTargetView(RetrieveUpdateDestroyAPIView):
    serializer_class = RevenueTargetSerializer
    queryset = RevenueTarget.objects.all()

    def get_object(self):
        revenue_target_id = self.kwargs.get('pk')
        try:
            revenue_target = RevenueTarget.objects.get(pk=revenue_target_id)
            return revenue_target
        except RevenueTarget.DoesNotExist:
            raise NotFound("Revenue target not found.")

    def retrieve(self, request, *args, **kwargs):
        total_revenue = Sale.objects.aggregate(total_revenue=Coalesce(Sum('amount'), 0))['total_revenue']

        revenue_target = self.get_object()

        covered_talktime = self.get_covered_talktime()

        response_data = {
            'target_revenue': revenue_target.target_revenue,
            'covered_revenue': total_revenue,
            'target_talktime': revenue_target.target_talktime,  
            'covered_talktime': covered_talktime,
        }

        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = RevenueTargetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_covered_talktime(self):
        total_talk_time = Sale.objects.aggregate(
            total_talktime=Coalesce(Sum('talktime'), 0)  
        )['total_talktime']

        return total_talk_time // 60 if total_talk_time else 0

    def patch(self, request, *args, **kwargs):
        revenue_target = self.get_object()
        serializer = RevenueTargetSerializer(revenue_target, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        revenue_target = self.get_object()
        revenue_target.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class RevenueCreateTargetView(generics.ListCreateAPIView):
    queryset = RevenueTarget.objects.all()
    serializer_class = RevenueTargetSerializer

    
class ExecutiveStatisticsAPIView(APIView):

    def get(self, request, executive_id):
        try:
            executive = Executives.objects.get(id=executive_id)
        except Executives.DoesNotExist:
            return Response({"detail": "Executive not found."}, status=status.HTTP_404_NOT_FOUND)

        total_coins_balance = executive.coins_balance

        today = timezone.now().date()
        total_days_offline = 0
        for day in range(30): 
            date = today - timezone.timedelta(days=day)
            if not ExecutiveCallHistory.objects.filter(executive=executive, start_time__date=date).exists():
                total_days_offline += 1

        total_rating = Rating.objects.filter(executive=executive).aggregate(total_rating=Sum('rating'))['total_rating'] or 0.0

        response_data = {
            'total_coins_balance': total_coins_balance,
            'total_days_offline': total_days_offline,
            'total_rating': total_rating,
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
class ExecutiveStatsAPIView(APIView):
    
    def get(self, request):
        total_executives = Executives.objects.count() 
        online_executives = Executives.objects.filter(online=True).count()
        offline_executives = Executives.objects.filter(online=False).count()

        response_data = {
            'total_executives': total_executives,
            'active_executives': online_executives,
            'inactive_executives': offline_executives,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class OngoingCallsAPIView(APIView):

    def get(self, request):
        ongoing_calls = ExecutiveCallHistory.objects.filter(status='accepted', end_time__isnull=True)
        
        ongoing_calls_data = []
        for call in ongoing_calls:
            duration = timezone.now() - call.start_time 
            ongoing_calls_data.append({
                'call_id': call.call_history.id,  
                'executive_name': call.executive.name,
                'user_id': call.user.user_id,  
                'start_time': call.start_time,
                'duration_minutes': duration.total_seconds() / 60,
            })

        return Response(ongoing_calls_data, status=status.HTTP_200_OK)


class ExecutiveStatsView(viewsets.ViewSet):
    serializer_class = ExecutiveStatsSerializer

    def retrieve(self, request, pk=None):
        try:
            executive = Executives.objects.get(pk=pk)
        except Executives.DoesNotExist:
            return Response({'error': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.serializer_class(executive)
        return Response(serializer.data)

    def update(self, request, pk=None):
        try:
            executive = Executives.objects.get(pk=pk)
        except Executives.DoesNotExist:
            return Response({'error': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.serializer_class(executive, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class CoinConversionListCreateView(generics.ListCreateAPIView):

    queryset = CoinConversion.objects.all()
    serializer_class = CoinConversionSerializer


class CallRatingCreateView(generics.CreateAPIView):
    queryset = CallRating.objects.all()
    serializer_class = CallRatingSerializer
    # permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user_id = self.kwargs.get('user_id')
        execallhistory_id = self.kwargs.get('execallhistory_id')

        data = request.data.copy()
        data['user'] = user_id
        data['execallhistory'] = execallhistory_id

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

# Retrieve, Update, Delete Rating
class CallRatingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CallRating.objects.all()
    serializer_class = CallRatingSerializer
    # permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "rating_id"

# List Ratings for a Specific Executive
class ExecutiveCallRatingListView(generics.ListAPIView):
    serializer_class = CallRatingSerializer
    # permission_classes = [IsAuthenticated]

    def get_queryset(self):
        executive_id = self.kwargs['executive_id']
        return CallRating.objects.filter(executive_id=executive_id)

# List All Ratings
class CallRatingListView(generics.ListAPIView):
    queryset = CallRating.objects.all()
    serializer_class = CallRatingSerializer
    # permission_classes = [IsAuthenticated]