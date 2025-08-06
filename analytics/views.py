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
from users.models import User,Rating
from calls.models import AgoraCallHistory,TalkTime,CallRating
from payments.models import PurchaseHistories
from django.utils.timezone import now
from django.utils import timezone
from datetime import timedelta
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
from django.db.models import Sum, F, ExpressionWrapper, DurationField, Avg, Count
from users.utils import send_otp_2factor
import random
from django.utils.timezone import make_aware
from datetime import datetime, time
import pytz


IST = pytz.timezone("Asia/Kolkata")

class PlatformAnalyticsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        now_dt = now().astimezone(IST)
        today = now_dt.date()
        ninety_days_ago = now_dt - timedelta(days=90)

        # Time boundaries
        start_of_today = IST.localize(datetime.combine(today, time.min))
        end_of_today = IST.localize(datetime.combine(today, time.max))
        start_of_week = IST.localize(datetime.combine(today - timedelta(days=today.weekday()), time.min))
        start_of_month = IST.localize(datetime.combine(today.replace(day=1), time.min))

        # Executives
        total_executives = Executives.objects.count()
        executives_today = Executives.objects.filter(created_at__date=today).count()
        executives_week = Executives.objects.filter(created_at__gte=start_of_week).count()
        executives_month = Executives.objects.filter(created_at__gte=start_of_month).count()
        active_executives = Executives.objects.filter(online=True).count()

        # Users
        total_users = User.objects.count()
        users_today = User.objects.filter(created_at__date=today).count()
        users_week = User.objects.filter(created_at__gte=start_of_week).count()
        users_month = User.objects.filter(created_at__gte=start_of_month).count()
        active_users = User.objects.filter(last_login__gte=ninety_days_ago).count()

        # Call metrics
        on_call = AgoraCallHistory.objects.filter(status="joined").count()

        today_duration_sum = AgoraCallHistory.objects.filter(start_time__date=today).aggregate(
            total_duration=Sum('duration')
        )['total_duration'] or timedelta(seconds=0)

        lifetime_duration_sum = AgoraCallHistory.objects.aggregate(
            total_duration=Sum('duration')
        )['total_duration'] or timedelta(seconds=0)

        def format_duration(duration_sum):
            if isinstance(duration_sum, timedelta):
                total_seconds = duration_sum.total_seconds()
            else:
                total_seconds = duration_sum or 0
            talk_time_minutes = total_seconds / 60
            return f"{int(talk_time_minutes)}" if talk_time_minutes == int(talk_time_minutes) else f"{talk_time_minutes:.2f}".replace('.00', '')

        formatted_today_talk_time = format_duration(today_duration_sum)
        formatted_total_talk_time = format_duration(lifetime_duration_sum)

        # Coin metrics
        user_coin_spending = AgoraCallHistory.objects.aggregate(
            total=Sum('coins_deducted')
        )['total'] or 0

        executive_coin_earnings = AgoraCallHistory.objects.aggregate(
            total=Sum('coins_added')
        )['total'] or 0

        # Revenue and coin sales
        purchases_all = PurchaseHistories.objects.filter(payment_status='SUCCESS')
        purchases_today = purchases_all.filter(purchase_date__range=(start_of_today, end_of_today))
        purchases_week = purchases_all.filter(purchase_date__gte=start_of_week)
        purchases_month = purchases_all.filter(purchase_date__gte=start_of_month)

        revenue_today = (
            purchases_today
            .filter(is_admin=False)
            .aggregate(total=Sum('recharge_plan__base_price'))['total'] or 0
        )
        revenue_week = purchases_week.aggregate(total=Sum('recharge_plan__base_price'))['total'] or 0
        revenue_month = purchases_month.aggregate(total=Sum('recharge_plan__base_price'))['total'] or 0
        revenue_all = (purchases_all .filter(is_admin=False) .aggregate(total=Sum('recharge_plan__base_price'))['total'] or 0)

        coins_today = (purchases_today.filter(is_admin=False).aggregate(total=Sum('coins_purchased'))['total'] or 0)
        coins_week = purchases_week.aggregate(total=Sum('coins_purchased'))['total'] or 0
        coins_month = purchases_month.aggregate(total=Sum('coins_purchased'))['total'] or 0
        coins_all = (purchases_all.filter(is_admin=False).aggregate(total=Sum('coins_purchased'))['total'] or 0)

        # Call details
        all_calls = AgoraCallHistory.objects.all().order_by('-start_time')
        call_details = [
            {
                "call_id": call.id,
                "executive_id": call.executive.id if call.executive else None,
                "executive_name": call.executive.name if call.executive else "Unknown",
                "user_id": call.user.id if call.user else None,
                "user_name": call.user.name if call.user else "Unknown",
                "status": call.status,
                "start_time": call.start_time.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S") if call.start_time else None,
                "end_time": call.end_time.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S") if call.end_time else None,
                "duration": call.duration.total_seconds() if hasattr(call.duration, 'total_seconds') else call.duration,
                "coins_deducted": call.coins_deducted,
                "coins_added": call.coins_added
            } for call in all_calls
        ]

        # Missed calls
        missed_calls = AgoraCallHistory.objects.filter(status="missed")
        today_total_calls = AgoraCallHistory.objects.filter(start_time__date=today).count()
        missed_call_count = missed_calls.count()
        missed_calls_today = missed_calls.filter(start_time__date=today)
        missed_call_count_today = missed_calls_today.count()
        missed_call_details = [
            {
                "call_id": call.id,
                "executive_id": call.executive.id if call.executive else None,
                "executive_name": call.executive.name if call.executive else "Unknown",
                "user_id": call.user.id if call.user else None,
                "user_name": call.user.name if call.user else "Unknown",
                "id": call.user.user_id if call.user else None,
                "executive_id": call.executive.executive_id if call.executive else None,
                "missed_at": call.start_time.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S") if call.start_time else None,
                "duration": call.duration.total_seconds() if hasattr(call.duration, 'total_seconds') else call.duration
            } for call in missed_calls
        ]

        return Response({
            # Executive metrics
            "total_executives": total_executives,
            "executives_today": executives_today,
            "executives_week": executives_week,
            "executives_month": executives_month,
            "active_executives": active_executives,

            # User metrics
            "total_users": total_users,
            "users_today": users_today,
            "users_week": users_week,
            "users_month": users_month,
            "active_users": active_users,

            # Call metrics
            "on_call": on_call,
            "today_talk_time": formatted_today_talk_time,
            "total_talk_time": formatted_total_talk_time,
            "user_coin_spending": user_coin_spending,
            "executive_coin_earnings": executive_coin_earnings,
            "total_missed_calls": missed_call_count,
            "missed_call_details": missed_call_details,
            "missed_calls_today": missed_call_count_today,
            "all_call_details": call_details,
            "total_calls": len(call_details),
            "today_total_calls": today_total_calls,

            # Revenue
            "revenue_today": revenue_today,
            "revenue_week": revenue_week,
            "revenue_month": revenue_month,
            "revenue_all_time": revenue_all,

            # Coin Sales
            "coin_sales_today": coins_today,
            "coin_sales_week": coins_week,
            "coin_sales_month": coins_month,
            "coin_sales_all_time": coins_all,
        }, status=status.HTTP_200_OK)
    
class ExecutiveAnalyticsView(APIView):
    def get(self, request, executive_id):
        executive = get_object_or_404(Executives, id=executive_id)
        today = now().date()

        # **Handle Period Parameter (Default: Lifetime)**
        period = request.query_params.get("period", None)  # '1d', '7d', '1m'
        if period == "7d":
            start_date = today - timedelta(days=7)
            total_days = 7
        elif period == "1m":
            start_date = today - timedelta(days=30)
            total_days = 30
        else:  # **Default: Lifetime Data**
            start_date = None
            total_days = None  # No fixed range

        # **Filter Calls Based on Period**
        call_filter = {"executive_id": executive.id}
        if start_date:
            call_filter["start_time__date__gte"] = start_date

        # **Total Calls**
        total_calls = AgoraCallHistory.objects.filter(**call_filter).count()

        # **Total Coins Earned**
        total_coins_earned = (
            AgoraCallHistory.objects.filter(**call_filter).aggregate(total=Sum("coins_added"))["total"]
            or 0
        )

        # **Total Talk Time (Convert timedelta to minutes)**
        total_talk_time_seconds = (
            AgoraCallHistory.objects.filter(**call_filter).aggregate(total=Sum("duration"))["total"]
            or timedelta()
        ).total_seconds()
        total_talk_time = round(total_talk_time_seconds / 60)  # Convert to minutes

        # **Last Call Details**
        last_call = (
            AgoraCallHistory.objects.filter(**call_filter)
            .order_by("-start_time")
            .first()
        )
        last_call_date = (
            last_call.start_time.strftime("%a, %d %b %I:%M %p") if last_call else "No Calls Yet"
        )

        # **Missed Calls**
        missed_calls = AgoraCallHistory.objects.filter(**call_filter, status="missed")
        missed_call_count = missed_calls.count()
        missed_call_details = [
            {
                "user_id": call.user.id if call.user else None,
                "user_name": call.user.name if call.user else "Unknown",
                "missed_at": call.start_time.strftime("%a, %d %b %I:%M %p")
                if call.start_time
                else "Unknown",
            }
            for call in missed_calls
        ]

        # **User Coin Spending**
        user_coin_spending = (
            AgoraCallHistory.objects.filter(**call_filter).aggregate(total=Sum("coins_deducted"))["total"]
            or 0
        )

        # **Coin Sales (Same as earnings)**
        coin_sales = total_coins_earned

        # **Average Call Duration**
        avg_call_duration = round(total_talk_time / total_calls, 2) if total_calls else 0

        # **Total Online Time (Convert timedelta to minutes)**
        total_online_seconds = executive.total_on_duty_seconds or 0
        total_online_minutes = round(total_online_seconds / 60)

        # **Total Calls Per Day (for Chart)**
        calls_per_day = (
            AgoraCallHistory.objects.filter(**call_filter)
            .values("start_time__date")
            .annotate(total_calls=Count("id"))
            .order_by("start_time__date")
        )

        # **Average Rating for Executive**
        avg_rating = (
            Rating.objects.filter(executive_id=executive.id)
            .filter(created_at__date__gte=start_date) if start_date else Rating.objects.filter(executive_id=executive.id)
        ).aggregate(avg=Avg("rating"))["avg"] or 0

        # **Online Days Calculation**
        online_days = (
            AgoraCallHistory.objects.filter(**call_filter)
            .values("start_time__date")
            .distinct()
            .count()
        )

        # **Offline Days Calculation**
        offline_days = (total_days - online_days) if total_days else "N/A (Lifetime Data)"

        return Response(
            {
                "executive_id": executive.id,
                "total_calls": total_calls,
                "total_coins_earned": total_coins_earned,
                "total_talk_time": f"{total_talk_time} Mins",
                "last_call_date": last_call_date,
                "earnings": total_coins_earned,
                "user_coin_spending": user_coin_spending,
                "coin_sales": coin_sales,
                "missed_calls_count": missed_call_count,
                "missed_call_details": missed_call_details,
                "avg_call_duration": f"{avg_call_duration} Mins",
                "total_online_time": f"{total_online_minutes} Mins",
                "calls_per_day": list(calls_per_day),
                "average_rating": round(avg_rating, 2),
                "online_days": online_days,
                "offline_days": offline_days,
                "period": period or "lifetime",
            },
            status=status.HTTP_200_OK,
        )
    
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
        return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

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
                'online': executive.online,
                'is_banned':executive.is_banned
            }, status=status.HTTP_200_OK)

        except Executives.DoesNotExist:
            return Response({'message': 'Executive not found.'}, status=status.HTTP_404_NOT_FOUND)


class CreateAdminView(generics.CreateAPIView):
    queryset = Admins.objects.all()
    serializer_class = AdminSerializer


class SendAdminOTPView(APIView):
    def post(self, request):
        mobile_number = request.data.get("mobile_number")

        if not mobile_number:
            return Response({"error": "Mobile number is required."}, status=400)

        try:
            admin = Admins.objects.get(mobile_number=mobile_number)
        except Admins.DoesNotExist:
            return Response({"error": "Admin with this mobile number not found."}, status=404)

        otp = str(random.randint(100000, 999999))

        try:
            send_otp_2factor(mobile_number, otp)
        except Exception as e:
            return Response({"error": f"Failed to send OTP: {str(e)}"}, status=500)

        admin.otp = otp
        admin.otp_created_at = timezone.now()
        admin.otp_attempts = 0
        admin.save()

        return Response({"message": "OTP sent successfully to mobile number."}, status=200)
    
class VerifyAdminOTPView(APIView):
    def post(self, request):
        mobile_number = request.data.get("mobile_number")
        otp = request.data.get("otp")

        if not mobile_number or not otp:
            return Response({"error": "Mobile number and OTP are required."}, status=400)

        try:
            admin = Admins.objects.get(mobile_number=mobile_number)
        except Admins.DoesNotExist:
            return Response({"error": "Admin not found."}, status=404)

        if not admin.otp or not admin.otp_created_at:
            return Response({"error": "OTP not generated."}, status=400)

        if timezone.now() > admin.otp_created_at + timedelta(minutes=5):
            return Response({"error": "OTP expired."}, status=400)

        if admin.otp != otp:
            admin.otp_attempts += 1
            admin.save()
            return Response({"error": "Invalid OTP."}, status=400)

        admin.otp = None
        admin.otp_created_at = None
        admin.otp_attempts = 0
        admin.save()

        request.session[f"otp_verified_{admin.id}"] = True

        return Response({"message": "OTP verified successfully."}, status=200)
    
class AdminDetailUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = Admins.objects.all()
    serializer_class = AdminSerializer


class SendPasswordResetOTPView(APIView):
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mobile_number = serializer.validated_data['mobile_number']

        try:
            admin = Admins.objects.get(mobile_number=mobile_number)
        except Admins.DoesNotExist:
            return Response({'message': 'Admin with this mobile number does not exist.'},
                            status=status.HTTP_404_NOT_FOUND)

        # Generate OTP
        otp = str(random.randint(100000, 999999))

        # Save OTP
        admin.otp = otp
        admin.otp_created_at = timezone.now()
        admin.otp_attempts = 0
        admin.save()

        # Send OTP via 2factor
        try:
            send_otp_2factor(mobile_number, otp)
        except Exception as e:
            return Response({'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {
                'message': 'OTP sent successfully',
                'expires_in': '5 minutes'
            },
            status=status.HTTP_200_OK
        )

class VerifyOTPResetPasswordView(APIView):
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        admin = serializer.validated_data['admin']
        new_password = serializer.validated_data['new_password']

        # Update password and clear OTP
        admin.set_password(new_password)
        admin.otp = None
        admin.otp_created_at = None
        admin.otp_attempts = 0
        admin.save()

        return Response(
            {'message': 'Password reset successfully'},
            status=status.HTTP_200_OK
        )



class ListAdminView(generics.ListAPIView):
    queryset = Admins.objects.all()
    serializer_class = AdminSerializer

class SuperuserLoginView(generics.GenericAPIView):
    serializer_class = SuperuserLoginSerializer 

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        admin = authenticate(request, email=email, password=password)
        if not admin:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        if not hasattr(admin, "role"):
            return Response({"detail": "This user does not have a role attribute."}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(admin)

        return Response({
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "user_id": admin.id,
            "email": admin.email,
            "role": admin.role, 
            "is_superuser": admin.is_superuser,
            "is_staff": admin.is_staff,
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
            return Response({'message': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)

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
            return Response({'message': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)

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
            return Response({'message': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)

        # Get filtering parameters
        period = request.query_params.get('period', None)  # 'today', 'week', 'month'

        # Default: Return full stats
        if not period:
            serializer = self.serializer_class(executive)
            response_data = serializer.data
            response_data.update({
                'status': 'success',
                'message': 'Full executive stats retrieved successfully'
            })
            return Response(response_data, status=status.HTTP_200_OK)

        # Define date ranges based on period
        today = timezone.now().date()
        if period == 'today':
            start_date = today
        elif period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)
        else:
            return Response({'message': 'Invalid period. Use "today", "week", or "month".'}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Filter call history for the given period
        filtered_calls = AgoraCallHistory.objects.filter(executive=executive, start_time__date__gte=start_date)

        # ✅ Calculate total duration safely
        total_calls = filtered_calls.count()
        total_duration = sum(call.duration.total_seconds() if call.duration else 0 for call in filtered_calls)

        # ✅ Serialize full executive details
        serializer = self.serializer_class(executive)
        response_data = serializer.data  # Get full executive details from serializer

        # ✅ Add calculated stats
        response_data.update({
            'total_calls': total_calls,
            'total_duration': total_duration,  # Duration in seconds
            'status': 'success',
            'message': f'Executive stats retrieved for {period}'
        })

        return Response(response_data, status=status.HTTP_200_OK)

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
    permission_classes = [AllowAny]

    def get_queryset(self):
        manager_id = self.kwargs.get("manager_id")
        return Executives.objects.filter(manager_executive_id=manager_id)

    def list(self, request, *args, **kwargs):
        manager_id = self.kwargs.get("manager_id")
        
        # Correct model for manager lookup
        manager = get_object_or_404(Admins, id=manager_id)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "manager_executive": manager.name,
            "executives": serializer.data
        })