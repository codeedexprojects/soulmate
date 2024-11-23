from rest_framework import serializers
from .models import *
from user.models import *
from django.db.models import Avg
from django.contrib.auth import authenticate
from datetime import datetime


class ExecutivesSerializer(serializers.ModelSerializer):
    rating = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    today_talk_time = serializers.SerializerMethodField()
    picked_calls = serializers.SerializerMethodField()
    missed_calls = serializers.SerializerMethodField()
    is_banned = serializers.BooleanField()
    is_suspended = serializers.BooleanField()
    call_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Executives
        fields = [
            'id',
            'name',
            'mobile_number',
            'email_id',
            'age',
            'online',
            'gender',
            'coins_per_second',
            'education_qualification',
            'profession',
            'skills',
            'place',
            'status',
            'executive_id',
            'set_coin',
            'duty_start_time',
            'total_on_duty_seconds',
            'total_talk_seconds_today',
            'total_picked_calls',
            'total_missed_calls',
            'rating',
            'is_favorited',
            'password',
            'today_talk_time',
            'picked_calls',
            'missed_calls',
            'is_banned',
            'is_suspended',
            'call_minutes',
            'coins_balance',
            'on_call',
        ]
        extra_kwargs = {
            'password': {'write_only': False}
        }


    def get_today_talk_time(self, obj):
        today = timezone.now().date()
        call_histories = ExecutiveCallHistory.objects.filter(executive=obj, start_time__date=today, status='picked')
        total_seconds = sum([ch.duration.total_seconds() for ch in call_histories])
        print(f"Total seconds today for {obj.name}: {total_seconds}")  # Debugging
        return total_seconds


    def get_picked_calls(self, obj):
        today = timezone.now().date()
        return ExecutiveCallHistory.objects.filter(executive=obj, start_time__date=today, status='picked').count()  

    def get_missed_calls(self, obj):
        today = timezone.now().date()
        return ExecutiveCallHistory.objects.filter(executive=obj, start_time__date=today, status='missed').count()  

    def get_rating(self, obj):
        return obj.rating_set.aggregate(Avg('rating'))['rating__avg'] or 0.0

    def get_is_favorited(self, obj):
        user_id = self.context.get('user_id', None)  # Default to None
        if user_id:
            return Favourite.objects.filter(user_id=user_id, executive=obj).exists()
        return False

    
    def get_call_minutes(self, obj):
        user = self.context.get('user')
        if user and obj.coins_per_second > 0:
            return user.coin_balance // obj.coins_per_second
        return 0


class ExecutiveLoginSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=15)
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        mobile_number = data.get('mobile_number')
        password = data.get('password')

        try:
            executive = Executives.objects.get(mobile_number=mobile_number)

            if executive.is_banned:
                raise serializers.ValidationError("This executive has been banned.")

            if executive.password != password:
                raise serializers.ValidationError('Invalid mobile number or password.')

        except Executives.DoesNotExist:
            raise serializers.ValidationError('Invalid mobile number or password.')

        return {
            'id': executive.id,
            'executive_id': executive.executive_id,
            'name': executive.name,
            'mobile_number': executive.mobile_number,
            'gender': executive.gender,
            'online': executive.online,
        }


class ExeCallHistorySerializer(serializers.ModelSerializer):
    call_date = serializers.SerializerMethodField()

    class Meta:
        model = ExecutiveCallHistory
        fields = ['executive', 'call_duration', 'coins_earned', 'call_date']

    def get_call_date(self, obj):
        return obj.call_date.strftime("%a, %d %b %I:%M %p")


class AdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Admins
        fields = ['email', 'name', 'password', 'is_staff', 'is_active', 'is_superuser', 'role']

    def create(self, validated_data):
        admin = Admins(
            email=validated_data['email'],
            name=validated_data['name'],
            is_staff=validated_data.get('is_staff', False),
            is_active=validated_data.get('is_active', True),
            is_superuser=validated_data.get('is_superuser', False),
            role=validated_data.get('role', 'other')
        )
        admin.set_password(validated_data['password']) 
        admin.save()
        return admin


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        user = authenticate(email=email, password=password)
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")

        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")

        if user.is_superuser:
            return {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'role': user.role,
                'is_superuser': user.is_superuser,
            }
        else:
            raise serializers.ValidationError("You do not have permission to login as admin.")

        return {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'role': user.role,
        }

class CallHistoryRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecutiveCallHistory
        fields = ['id', 'rating']

    def validate_rating(self, value):
        if not (0 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 0 and 5.")
        return value



class CoinRedemptionRequestSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='executive.name', read_only=True)

    class Meta:
        model = CoinRedemptionRequest
        fields = ['id', 'executive','name', 'amount_requested', 'upi_id', 'request_time', 'status','created_at']
        read_only_fields = ['executive', 'amount_requested', 'created_at', 'status']


from datetime import timedelta

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        admin = Admins.objects.filter(email=email).first()
        
        if admin is None:
            raise serializers.ValidationError("User with this email does not exist.")
        
        if not admin.check_password(password):
            raise serializers.ValidationError("Invalid credentials.")
        
        data['admin'] = admin
        return data

class RevenueTargetSerializer(serializers.ModelSerializer):
    target_talktime_display = serializers.SerializerMethodField()

    class Meta:
        model = RevenueTarget
        fields = ['id', 'created_at', 'target_revenue', 'target_talktime', 'target_talktime_display']

    def get_target_talktime_display(self, obj):
        if obj.target_talktime:
            total_minutes = obj.target_talktime.total_seconds() // 60
            return int(total_minutes)
        return None

    def validate_target_talktime(self, value):
        if isinstance(value, int):
            return datetime.timedelta(minutes=value)
        return value

    def update(self, instance, validated_data):
        target_talktime = validated_data.get('target_talktime', instance.target_talktime)
        if isinstance(target_talktime, int):
            validated_data['target_talktime'] = datetime.timedelta(minutes=target_talktime)
        return super().update(instance, validated_data)

class ExecutiveStatsSerializer(serializers.ModelSerializer):
    total_online_minutes = serializers.SerializerMethodField()
    total_talktime_minutes = serializers.SerializerMethodField()
    total_accepted_calls = serializers.SerializerMethodField()
    total_missed_calls = serializers.SerializerMethodField()
    coins_balance = serializers.IntegerField()
    coins_earned_today = serializers.SerializerMethodField()
    progression_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Executives
        fields = [
            'name',
            'total_online_minutes',
            'total_talktime_minutes',
            'total_accepted_calls',
            'total_missed_calls',
            'coins_balance',
            'coins_earned_today',
            'progression_percentage'
        ]

    def get_total_online_minutes(self, obj):
        """
        Calculate the total lifetime online time in minutes (hh:mm:ss format).
        Only consider periods where `online=True`.
        """
        if obj.online and obj.duty_start_time:
            # Current online session time
            current_online_time = (timezone.now() - obj.duty_start_time).total_seconds()
        else:
            current_online_time = 0

        # Total lifetime online time in seconds
        total_online_seconds = obj.total_on_duty_seconds + current_online_time

        # Convert to hours, minutes, and seconds
        hours = int(total_online_seconds // 3600)
        minutes = int((total_online_seconds % 3600) // 60)
        seconds = int(total_online_seconds % 60)

        return f"{hours:02}:{minutes:02}:{seconds:02}"  # Format as hh:mm:ss

    def get_total_talktime_minutes(self, obj):
        """
        Calculate the total talktime in minutes for all calls associated with the executive.
        """
        # Sum up the `duration` of all accepted calls
        total_seconds = ExecutiveCallHistory.objects.filter(
            executive=obj, status='accepted'
        ).aggregate(total_duration=models.Sum('duration'))['total_duration'] or timedelta()

        # Convert seconds to minutes (hh:mm:ss format)
        total_seconds = total_seconds.total_seconds() if isinstance(total_seconds, timedelta) else total_seconds
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)

        return f"{hours:02}:{minutes:02}:{seconds:02}"  # Format as hh:mm:ss

    def get_total_accepted_calls(self, obj):
        """
        Count the total number of accepted calls.
        """
        return ExecutiveCallHistory.objects.filter(executive=obj, status='accepted').count()

    def get_total_missed_calls(self, obj):
        """
        Count the total number of missed calls.
        """
        return ExecutiveCallHistory.objects.filter(executive=obj, status='missed').count()

    def get_coins_earned_today(self, obj):
        """
        Calculate the total coins earned today (added to `coins_balance` today).
        """
        start_of_day = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_earnings = ExecutiveCallHistory.objects.filter(
            executive=obj,
            status='accepted',
            start_time__gte=start_of_day
        ).aggregate(today_coins=models.Sum('coins_earned'))['today_coins'] or 0

        return today_earnings

    def get_progression_percentage(self, obj):
        """
        Calculate progression percentage based on current online session hours.
        """
        if obj.online and obj.duty_start_time:
            current_online_time_hours = (timezone.now() - obj.duty_start_time).total_seconds() / 3600
            progression = min((current_online_time_hours / 3) * 0.01, 0.100)
            return progression
        return 0.01


    

class CoinConversionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinConversion
        fields = ['id', 'coins_earned', 'rupees']


class CallRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallRating
        fields = ['id', 'executive', 'user', 'execallhistory', 'stars', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']



