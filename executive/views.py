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

from django.db.models import Avg

class ListExecutivesByUserView(generics.ListAPIView):
    serializer_class = ExecutivesSerializer

    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        if not user_id:
            raise NotFound("User ID is required.")

        # Exclude executives who have blocked the user
        blocked_executives = UserBlock.objects.filter(user_id=user_id, is_blocked=True).values_list('executive_id', flat=True)

        # Annotate each executive with their average rating
        queryset = Executives.objects.filter(
            is_suspended=False,
            is_banned=False
        ).exclude(
            id__in=blocked_executives  # Exclude executives that have blocked the user
        ).annotate(
            average_rating=Avg('call_ratings__stars')  # Using related_name from CallRating model
        ).order_by(
            '-online',  # First order by online status (True first)
            '-average_rating'  # Then by highest average rating
        )

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['user_id'] = self.kwargs['user_id']
        context['request'] = self.request
        return context

from rest_framework.generics import ListAPIView


# class TalkTimeHistoryByExecutiveView(ListAPIView):
#     serializer_class = TalkTimeHistorySerializer

#     def get_queryset(self):
#         executive_id = self.kwargs.get('executive_id')
#         if not executive_id:
#             raise NotFound("Executive ID is required.")
        
#         # Filter TalkTime using the related AgoraCallHistory model
#         return TalkTime.objects.filter(
#             call_history__executive_id=executive_id
#         ).select_related('call_history').order_by('-call_history__start_time')



class TalkTimeHistoryByExecutiveView(ListAPIView):
    serializer_class = TalkTimeHistorySerializer

    def get_queryset(self):
        executive_id = self.kwargs.get('executive_id')
        if not executive_id:
            raise NotFound("Executive ID is required.")

        try:
            # Ensure the executive exists before querying
            Executives.objects.get(id=executive_id)
        except Executives.DoesNotExist:
            raise NotFound(f"Executive with ID {executive_id} does not exist.")

        queryset = AgoraCallHistory.objects.filter(executive_id=executive_id).order_by('-start_time')

        if not queryset.exists():
            raise NotFound(f"No call history found for executive ID: {executive_id}")

        return queryset

class TalkTimeHistoryByExecutiveAndUserView(ListAPIView):
    serializer_class = TalkTimeHistorySerializer

    def get_queryset(self):
        executive_id = self.kwargs.get('executive_id')
        user_id = self.kwargs.get('user_id')

        # Ensure both executive_id and user_id are provided
        if not executive_id or not user_id:
            raise NotFound("Both Executive ID and User ID are required.")

        try:
            # Ensure the executive exists before querying
            executive = Executives.objects.get(id=executive_id)
        except Executives.DoesNotExist:
            raise NotFound(f"Executive with ID {executive_id} does not exist.")

        # Query the call history for the given executive and user, ordered by start_time (most recent first)
        queryset = AgoraCallHistory.objects.filter(executive_id=executive_id, user_id=user_id).order_by('-start_time')

        # Return only the last 5 records
        return queryset[:5]





class TalkTimeHistoryByExecutiveMinimalView(ListAPIView):
    serializer_class = TalkTimeHistoryMinimalSerializer

    def get_queryset(self):
        executive_id = self.kwargs.get('executive_id')
        if not executive_id:
            raise NotFound("Executive ID is required.")

        return TalkTime.objects.filter(executive_id=executive_id)

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
        try:
            # Fetch the executive
            executive = Executives.objects.get(id=executive_id)

            # Calculate total on-duty time
            total_on_duty = str(timedelta(seconds=executive.total_on_duty_seconds))
            if executive.online and executive.duty_start_time:
                current_session_duration = now() - executive.duty_start_time
                total_on_duty = str(
                    timedelta(seconds=executive.total_on_duty_seconds + current_session_duration.total_seconds())
                )

            # Filter today's call history for the executive
            start_of_day = now().replace(hour=0, minute=0, second=0, microsecond=0)
            call_history_today = AgoraCallHistory.objects.filter(
                executive=executive,
                start_time__gte=start_of_day
            )

            # Calculate total talk time today
            total_talk_time_today_seconds = sum(
                [call.duration.total_seconds() for call in call_history_today if call.duration]
            )
            total_talk_time_today = str(timedelta(seconds=total_talk_time_today_seconds))

            # Calculate total joined and missed calls
            total_joined_calls = call_history_today.filter(status="joined").count()
            total_missed_calls = call_history_today.filter(status="missed").count()

            # Return response
            return Response({
                'id': executive.id,
                'executive_name': executive.name,
                'total_on_duty_time': total_on_duty,
                'total_talk_time_today': total_talk_time_today,
                'total_joined_calls': total_joined_calls,
                'total_missed_calls': total_missed_calls,
                'online': executive.online
            }, status=status.HTTP_200_OK)

        except Executives.DoesNotExist:
            return Response({'error': 'Executive not found.'}, status=status.HTTP_404_NOT_FOUND)

from decimal import Decimal, DivisionByZero

from .tasks import *
from threading import Timer


from agora_token_builder import RtcTokenBuilder
import time
import requests
import logging

AGORA_API_KEY = "6f148332fbc1404e80c0de9024484dde"

logger = logging.getLogger(__name__)


from django.core.cache import cache

# Agora credentials
AGORA_APP_ID = '9626e8b5f847e6961cb9a996e1ae93'
AGORA_APP_CERTIFICATE = 'ab41eb854807425faa1b44481ff97fe3'

    
class ExeCallHistoryListView(generics.ListAPIView):
    serializer_class = ExeCallHistorySerializer

    def get_queryset(self):
        executive_id = self.kwargs['executive_id']
        return AgoraCallHistory.objects.filter(executive_id=executive_id)


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
    queryset = AgoraCallHistory.objects.all()
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
        call_histories = AgoraCallHistory.objects.filter(executive=executive)

        # Serialize the data using CallHistorySerializer
        serializer = CallHistorySerializer(call_histories, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


from rest_framework.generics import RetrieveUpdateDestroyAPIView

from django.db.models import Sum, DurationField, IntegerField
from django.db.models.functions import Coalesce

class RevenueTargetView(RetrieveUpdateDestroyAPIView):
    serializer_class = RevenueTargetSerializer
    queryset = RevenueTarget.objects.all()

    def get_object(self):
        revenue_target_id = self.kwargs.get('pk')
        try:
            return RevenueTarget.objects.get(pk=revenue_target_id)
        except RevenueTarget.DoesNotExist:
            raise NotFound("Revenue target not found.")

    def retrieve(self, request, *args, **kwargs):
        revenue_target = self.get_object()

        # Calculate covered revenue
        covered_revenue = Sale.objects.aggregate(
            total_revenue=Coalesce(Sum('amount'), 0)
        )['total_revenue']

        # Calculate covered talktime from AgoraCallHistory
        covered_talktime = self.get_covered_talktime()

        response_data = {
            'target_revenue': revenue_target.target_revenue,
            'covered_revenue': covered_revenue,
            'target_talktime': revenue_target.target_talktime,
            'covered_talktime': covered_talktime,
        }

        return Response(response_data, status=status.HTTP_200_OK)

    def get_covered_talktime(self):
        # Aggregate total duration from AgoraCallHistory, specify output_field to handle the mixed types
        total_duration = AgoraCallHistory.objects.aggregate(
            total_duration=Coalesce(Sum('duration'), timedelta(0), output_field=DurationField())
        )['total_duration']

        # Convert total duration to minutes
        if total_duration:
            total_minutes = total_duration.total_seconds() // 60
            return total_minutes
        return 0

    def post(self, request, *args, **kwargs):
        serializer = RevenueTargetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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


from django.db.models import Avg, Count

class ExecutiveStatisticsAPIView(APIView):

    def get(self, request, executive_id):
        # Fetch the executive or return a 404 response
        try:
            executive = Executives.objects.get(id=executive_id)
        except Executives.DoesNotExist:
            return Response({"detail": "Executive not found."}, status=status.HTTP_404_NOT_FOUND)

        # Calculate total coins balance
        total_coins_balance = executive.coins_balance

        # Calculate total offline days in the last 30 days (no calls and executive was not online)
        today = timezone.now().date()
        last_30_days = [today - timezone.timedelta(days=i) for i in range(30)]

        offline_days = 0
        for day in last_30_days:
            # Check if the executive did not make any calls and their status was offline
            if not AgoraCallHistory.objects.filter(executive=executive, start_time__date=day).exists() and not executive.online:
                offline_days += 1

        # Calculate total ratings (average rating of all ratings)
        total_ratings = CallRating.objects.filter(executive=executive)

        if total_ratings.exists():
            # Calculate the average rating (stars)
            average_rating = total_ratings.aggregate(average_rating=Avg('stars'))['average_rating'] or 0.0
            total_rating = round(average_rating, 2)
        else:
            total_rating = "No ratings yet"

        # Response data
        response_data = {
            'total_coins_balance': total_coins_balance,
            'total_days_offline': offline_days,
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
        ongoing_calls = AgoraCallHistory.objects.filter(status='joined', end_time__isnull=True)

        ongoing_calls_data = []
        for call in ongoing_calls:
            duration = timezone.now() - call.start_time
            ongoing_calls_data.append({
                'call_id': call.id,
                'executive_name': call.executive.name,
                'user_id': call.user.user_id,
                'start_time': call.start_time,
                'duration_minutes': duration.total_seconds() / 60,
                'channel_name':call.channel_name,
                'token':call.executive_token,
                'uid':call.uid,
                'executive_id':call.executive.id,
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
        response_data = serializer.data
        response_data.update({
            'status': 'success',
            'message': 'Executive stats retrieved successfully'
        })
        return Response(response_data, status=status.HTTP_200_OK)

    def update(self, request, pk=None):
        try:
            executive = Executives.objects.get(pk=pk)
        except Executives.DoesNotExist:
            return Response({'error': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(executive, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            response_data.update({
                'status': 'success',
                'message': 'Executive stats updated successfully'
            })
            return Response(response_data, status=status.HTTP_200_OK)
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

class UpdateExecutiveOnCallStatus(APIView):
    def post(self, request, executive_id):
        # Get the executive object by ID
        executive = get_object_or_404(Executives, id=executive_id)

        # Deserialize the incoming data
        serializer = ExecutiveOnCallSerializer(executive, data=request.data, partial=True)
        if serializer.is_valid():
            # Save the updated on_call status
            serializer.save()
            return Response({
                'message': 'Executive on_call status updated successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class TotalCoinsDeductedView(APIView):
    def get(self, request, user_id):
        # Validate if user exists
        user = get_object_or_404(User, user_id=user_id)

        # Calculate total coins deducted from AgoraCallHistory for the given user
        total_coins = AgoraCallHistory.objects.filter(user=user).aggregate(
            total_deducted=Sum('coins_deducted')
        )['total_deducted'] or 0

        return Response({
            'user_id': user_id,
            'total_coins_deducted': total_coins
        }, status=status.HTTP_200_OK)

class DeleteExecutiveAccountView(APIView):
    def delete(self, request, executive_id, *args, **kwargs):
        # Retrieve the executive by ID
        executive = get_object_or_404(Executives, id=executive_id)

        # Delete the executive
        executive.delete()

        return Response(
            {"message": f"Executive with ID {executive_id} has been deleted successfully."},
            status=status.HTTP_200_OK
        )
    
class ExecutiveProfilePictureView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, executive_id):
        """Get the profile picture of a specific executive."""
        try:
            profile_picture = ExecutiveProfilePicture.objects.get(executive__executive_id=executive_id)
            serializer = ExecutiveProfilePictureSerializer(profile_picture)
            return Response(serializer.data)
        except ExecutiveProfilePicture.DoesNotExist:
            return Response({"detail": "Profile picture not found."}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, executive_id):
        """Create a profile picture for an executive."""
        try:
            executive = Executives.objects.get(executive_id=executive_id)
        except Executives.DoesNotExist:
            return Response({"detail": "Executive not found."}, status=status.HTTP_404_NOT_FOUND)

        # Prepare the data for serializer, ensuring it is mutable
        data = request.data.copy()  # Make request data mutable
        data['executive'] = executive.id  # Set the executive ID for the profile picture

        # Use the serializer to validate and save the data
        serializer = ExecutiveProfilePictureSerializer(data=data)
        if serializer.is_valid():
            # Check if the executive already has a profile picture
            existing_profile_picture = ExecutiveProfilePicture.objects.filter(executive=executive).first()
            if existing_profile_picture:
                return Response({"detail": "Profile picture already exists."}, status=status.HTTP_400_BAD_REQUEST)

            # Save the profile picture
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        # If the serializer is not valid, return errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, executive_id):
        """Approve or reject the profile picture for the executive."""
        try:
            profile_picture = ExecutiveProfilePicture.objects.get(executive__executive_id=executive_id)
        except ExecutiveProfilePicture.DoesNotExist:
            return Response({"detail": "Profile picture not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get the status from the request data
        status_value = request.data.get('status')
        if status_value and status_value in ['approved', 'rejected']:
            # Update the profile picture status
            if status_value == 'approved':
                profile_picture.approve()
            elif status_value == 'rejected':
                profile_picture.reject()

            # Return the updated status of the profile picture
            return Response({"status": profile_picture.status}, status=status.HTTP_200_OK)
        
        return Response({"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)