from django.shortcuts import render
from rest_framework import status, generics,viewsets
from .models import *
from .serializers import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from datetime import  timedelta
from .models import *
from .serializers import *
from executives.models import Executives
from users.models import User
from calls.models import AgoraCallHistory,TalkTime,CallRating
from payments.models import PurchaseHistory
from django.utils.timezone import now
from django.utils import timezone
from rest_framework.decorators import api_view
from calls.serializers import TalkTimeHistorySerializer,TalkTimeHistoryMinimalSerializer,CallHistorySerializer,CallRatingSerializer,ExecutiveOnCallSerializer
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView
from executives.serializers import ExecutivesSerializer
from django.contrib.auth import logout
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from payments.models import Sale
from django.db.models.functions import Coalesce
from django.db.models import Sum, DurationField
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, AllowAny

class PlatformAnalyticsView(APIView):
    def get(self, request):
        today = now().date()
        ninety_days_ago = now() - timedelta(days=90)

        total_executives = Executives.objects.count()
        total_users = User.objects.count()

        active_executives = Executives.objects.filter(last_login__gte=ninety_days_ago).count()
        active_users = User.objects.filter(last_login__gte=ninety_days_ago).count()

        on_call = AgoraCallHistory.objects.filter(status="joined").count()

        today_talk_time = AgoraCallHistory.objects.filter(start_time__date=today).aggregate(
            total_minutes=Sum('duration'))['total_minutes'] or 0

        todays_revenue = PurchaseHistory.objects.filter(purchase_date__date=today).aggregate(
            total=Sum('purchased_price'))['total'] or 0

        todays_coin_sales = PurchaseHistory.objects.filter(purchase_date__date=today).aggregate(
            total=Sum('coins_purchased'))['total'] or 0

        # **Fix: Replace coins_spent with coins_deducted**
        user_coin_spending = AgoraCallHistory.objects.filter(start_time__date=today).aggregate(
            total=Sum('coins_deducted'))['total'] or 0

        executive_coin_earnings = AgoraCallHistory.objects.filter(start_time__date=today).aggregate(
            total=Sum('coins_added'))['total'] or 0

        missed_calls = AgoraCallHistory.objects.filter(status="missed", start_time__date=today).count()

        return Response({
            "total_executives": total_executives,
            "total_users": total_users,
            "todays_revenue": f"₹{todays_revenue}",
            "todays_coin_sales": todays_coin_sales,
            "active_executives": active_executives,
            "active_users": active_users,
            "on_call": on_call,
            "today_talk_time": f"{today_talk_time} Mins",
            "user_coin_spending": user_coin_spending,
            "executive_coin_earnings": executive_coin_earnings,
            "missed_calls": missed_calls
        }, status=status.HTTP_200_OK)



class ExecutiveAnalyticsView(APIView):
    def get(self, request, executive_id):
        executive = get_object_or_404(Executives, id=executive_id)
        today = now().date()

        total_calls = AgoraCallHistory.objects.filter(executive=executive).count()

        total_coins_earned = AgoraCallHistory.objects.filter(executive=executive).aggregate(
            total=Sum('coins_added'))['total'] or 0

        total_talk_time_seconds = AgoraCallHistory.objects.filter(executive=executive).aggregate(
            total=Sum('duration'))['total'] or 0
        total_talk_time = round(total_talk_time_seconds.total_seconds() / 60) if total_talk_time_seconds else 0

        last_call = AgoraCallHistory.objects.filter(executive=executive).order_by('-start_time').first()
        last_call_date = last_call.start_time.strftime("%a, %d %b %I:%M %p") if last_call and last_call.start_time else "No Calls Yet"

        todays_earnings = AgoraCallHistory.objects.filter(executive=executive, start_time__date=today).aggregate(
            total=Sum('coins_added'))['total'] or 0

        # **New Report Data**
        duty_reports = AgoraCallHistory.objects.filter(executive=executive, start_time__date=today).count()

        missed_calls = AgoraCallHistory.objects.filter(executive=executive, status="missed", start_time__date=today).count()

        return Response({
            "executive_id": executive.id,
            "total_calls": total_calls,
            "total_coins_earned": total_coins_earned,
            "total_talk_time": f"{total_talk_time} Mins",
            "last_call_date": last_call_date,
            "todays_earnings": todays_earnings,
            "duty_reports": duty_reports,
            "missed_calls": missed_calls
        }, status=status.HTTP_200_OK)
    
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
    
@api_view(['GET'])
def call_history(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    call_history = AgoraCallHistory.objects.filter(user=user).order_by('-start_time')

    serializer = CallHistorySerializer(call_history, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


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
    
class TalkTimeHistoryByExecutiveView(ListAPIView):
    serializer_class = TalkTimeHistorySerializer

    def get_queryset(self):
        executive_id = self.kwargs.get('executive_id')
        if not executive_id:
            raise NotFound("Executive ID is required.")

        try:
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

        if not executive_id or not user_id:
            raise NotFound("Both Executive ID and User ID are required.")

        try:
            executive = Executives.objects.get(id=executive_id)
        except Executives.DoesNotExist:
            raise NotFound(f"Executive with ID {executive_id} does not exist.")

        queryset = AgoraCallHistory.objects.filter(executive_id=executive_id, user_id=user_id).order_by('-start_time')

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

class ExecutiveStatusView(APIView):
    def get(self, request, executive_id):
        try:
            executive = Executives.objects.get(id=executive_id)

            total_on_duty = str(timedelta(seconds=executive.total_on_duty_seconds))
            if executive.online and executive.duty_start_time:
                current_session_duration = now() - executive.duty_start_time
                total_on_duty = str(
                    timedelta(seconds=executive.total_on_duty_seconds + current_session_duration.total_seconds())
                )

            start_of_day = now().replace(hour=0, minute=0, second=0, microsecond=0)
            call_history_today = AgoraCallHistory.objects.filter(
                executive=executive,
                start_time__gte=start_of_day
            )

            total_talk_time_today_seconds = sum(
                [call.duration.total_seconds() for call in call_history_today if call.duration]
            )
            total_talk_time_today = str(timedelta(seconds=total_talk_time_today_seconds))

            total_joined_calls = call_history_today.filter(status="joined").count()
            total_missed_calls = call_history_today.filter(status="missed").count()

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


class CreateAdminView(generics.CreateAPIView):
    queryset = Admins.objects.all()
    serializer_class = AdminSerializer

class ListAdminView(generics.ListAPIView):
    queryset = Admins.objects.all()
    serializer_class = AdminSerializer

class SuperuserLoginView(generics.GenericAPIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        admin = authenticate(request, email=email, password=password)
        if not admin:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(admin)

        return Response({
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "user_id": admin.id,
            "email": admin.email,
            "name": admin.name,
            "role": admin.role, 
            "is_superuser": admin.is_superuser,
            "is_staff": admin.is_staff
        }, status=status.HTTP_200_OK)

class AdminLogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({"message": "Logged out successfully"})


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

        covered_revenue = Sale.objects.aggregate(
            total_revenue=Coalesce(Sum('amount'), 0)
        )['total_revenue']

        covered_talktime = self.get_covered_talktime()

        response_data = {
            'target_revenue': revenue_target.target_revenue,
            'covered_revenue': covered_revenue,
            'target_talktime': revenue_target.target_talktime,
            'covered_talktime': covered_talktime,
        }

        return Response(response_data, status=status.HTTP_200_OK)

    def get_covered_talktime(self):
        total_duration = AgoraCallHistory.objects.aggregate(
            total_duration=Coalesce(Sum('duration'), timedelta(0), output_field=DurationField())
        )['total_duration']

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

class ExecutiveStatisticsAPIView(APIView):

    def get(self, request, executive_id):
        try:
            executive = Executives.objects.get(id=executive_id)
        except Executives.DoesNotExist:
            return Response({"detail": "Executive not found."}, status=status.HTTP_404_NOT_FOUND)

        total_coins_balance = executive.coins_balance

        today = timezone.now().date()
        last_30_days = [today - timezone.timedelta(days=i) for i in range(30)]

        offline_days = 0
        for day in last_30_days:
            if not AgoraCallHistory.objects.filter(executive=executive, start_time__date=day).exists() and not executive.online:
                offline_days += 1

        total_ratings = CallRating.objects.filter(executive=executive)

        if total_ratings.exists():
            average_rating = total_ratings.aggregate(average_rating=Avg('stars'))['average_rating'] or 0.0
            total_rating = round(average_rating, 2)
        else:
            total_rating = "No ratings yet"

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

import logging
logger = logging.getLogger(__name__)

class UpdateExecutiveOnCallStatus(APIView):
    def post(self, request, executive_id):
        executive = get_object_or_404(Executives, id=executive_id)
        
        logger.debug(f"Request Data: {request.data}")
        logger.debug(f"Current on_call (Before): {executive.on_call}")

        serializer = ExecutiveOnCallSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Serializer Errors: {serializer.errors}")
            return Response(serializer.errors, status=400)

        new_on_call = serializer.validated_data.get('on_call')
        logger.debug(f"Validated on_call: {new_on_call}")

        executive.on_call = new_on_call
        executive.save(update_fields=["on_call"])  
        executive.refresh_from_db()

        logger.debug(f"Updated on_call (After): {executive.on_call}")

        return Response({
            'message': 'Executive on_call status updated successfully.',
            'on_call': executive.on_call
        }, status=status.HTTP_200_OK)



class TotalCoinsDeductedView(APIView):
    def get(self, request, user_id):
        user = get_object_or_404(User, user_id=user_id)

        total_coins = AgoraCallHistory.objects.filter(user=user).aggregate(
            total_deducted=Sum('coins_deducted')
        )['total_deducted'] or 0

        return Response({
            'user_id': user_id,
            'total_coins_deducted': total_coins
        }, status=status.HTTP_200_OK)



class ExecutivesUnderManagerView(generics.ListAPIView):
    serializer_class = ExecutivesSerializer
    permission_classes = [AllowAny]  # No authentication required

    def get_queryset(self):
        manager_id = self.kwargs.get("manager_id")  # Get manager ID from URL
        return Executives.objects.filter(manager_executive=manager_id)

    def list(self, request, *args, **kwargs):
        manager_id = self.kwargs.get("manager_id")
        
        # Ensure the manager exists
        manager = get_object_or_404(Executives, id=manager_id)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "manager_executive": manager.name,
            "executives": serializer.data
        })