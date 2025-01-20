from rest_framework import serializers
from .models import *
from user.models import *
from user.models import AgoraCallHistory
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
    profile_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Executives
        fields = [
            'id',
            'name',
            'mobile_number',
            'profile_photo_url',
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
        call_histories = AgoraCallHistory.objects.filter(
            executive=obj, start_time__date=today, status='left'
        )
        # Handle cases where duration might be None
        total_seconds = sum([ch.duration.total_seconds() for ch in call_histories if ch.duration])
        return total_seconds or 0  # Return 0 if no calls or durations are None
    
    def get_profile_photo_url(self, obj):
        profile_picture = ExecutiveProfilePicture.objects.filter(executive=obj).first()

        if profile_picture:
            if profile_picture.status == 'approved':
                request = self.context.get('request')
                # Build absolute URL if request context is available
                return request.build_absolute_uri(profile_picture.profile_photo.url) if request else profile_picture.profile_photo.url
            elif profile_picture.status == 'pending':
                return "waiting for approval"

        return None


    def get_picked_calls(self, obj):
        today = timezone.now().date()
        return AgoraCallHistory.objects.filter(
            executive=obj, start_time__date=today, status='left'
        ).count() or 0

    def get_missed_calls(self, obj):
        today = timezone.now().date()
        return AgoraCallHistory.objects.filter(
            executive=obj, start_time__date=today, status='missed'
        ).count() or 0


    def get_rating(self, obj):
    # Use the related name for CallRating model
        average_rating = obj.call_ratings.aggregate(average_stars=models.Avg('stars'))['average_stars'] or 0.0
        return round(average_rating, 2)


    def get_is_favorited(self, obj):
        user_id = self.context.get('user_id', None)  # Default to None
        if user_id:
            return Favourite.objects.filter(user_id=user_id, executive=obj).exists()
        return False


    def get_call_minutes(self, obj):
        user = self.context.get('user')  # Fetch user from context
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
        model = AgoraCallHistory
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
        model = AgoraCallHistory
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
        # Convert target_talktime to total minutes for display
        if obj.target_talktime:
            total_minutes = obj.target_talktime.total_seconds() // 60
            return int(total_minutes)
        return None

    def validate_target_talktime(self, value):
        # If the value is in minutes (int), convert to timedelta
        if isinstance(value, int):
            return datetime.timedelta(minutes=value)
        return value

    def update(self, instance, validated_data):
        target_talktime = validated_data.get('target_talktime', instance.target_talktime)
        # Ensure target_talktime is in timedelta format
        if isinstance(target_talktime, int):
            validated_data['target_talktime'] = datetime.timedelta(minutes=target_talktime)
        return super().update(instance, validated_data)

    def create(self, validated_data):
        # Ensure target_talktime is in timedelta format
        target_talktime = validated_data.get('target_talktime')
        if isinstance(target_talktime, int):
            validated_data['target_talktime'] = datetime.timedelta(minutes=target_talktime)
        return super().create(validated_data)

class ExecutiveCallHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AgoraCallHistory
        fields = ['id','executive', 'status', 'start_time', 'end_time']

from django.db.models import Sum, F


class ExecutiveStatsSerializer(serializers.ModelSerializer):
    total_online_minutes = serializers.SerializerMethodField()
    total_talktime_minutes = serializers.SerializerMethodField()
    total_accepted_calls = serializers.SerializerMethodField()
    total_missed_calls = serializers.SerializerMethodField()
    coins_balance = serializers.FloatField()
    coins_earned_today = serializers.SerializerMethodField()
    progression_percentage = serializers.SerializerMethodField()
    minutes_talked_today = serializers.SerializerMethodField()

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
            'progression_percentage',
            'minutes_talked_today',
        ]

    def get_total_online_minutes(self, obj):
        current_online_time = (now() - obj.duty_start_time).total_seconds() if obj.online and obj.duty_start_time else 0
        total_online_seconds = obj.total_on_duty_seconds + current_online_time
        return int(total_online_seconds // 60)

    def get_total_talktime_minutes(self, obj):
        total_duration = AgoraCallHistory.objects.filter(
            executive=obj, status='left'
        ).aggregate(total_duration=models.Sum('duration'))['total_duration'] or timedelta(0)

        return round(total_duration.total_seconds() / 60, 2)

    def get_total_accepted_calls(self, obj):
        start_of_day = now().replace(hour=0, minute=0, second=0, microsecond=0)
        return AgoraCallHistory.objects.filter(executive=obj, status='left', start_time__gte=start_of_day).count()

    def get_total_missed_calls(self, obj):
        start_of_day = now().replace(hour=0, minute=0, second=0, microsecond=0)
        return AgoraCallHistory.objects.filter(executive=obj, status='missed', start_time__gte=start_of_day).count()

    def get_coins_earned_today(self, obj):
        start_of_day = now().replace(hour=0, minute=0, second=0, microsecond=0)
        return float(
            AgoraCallHistory.objects.filter(
                executive=obj, start_time__gte=start_of_day
            ).aggregate(coins_earned=models.Sum('coins_deducted'))['coins_earned'] or 0
        )

    def get_progression_percentage(self, obj):
        start_of_day = now().replace(hour=0, minute=0, second=0, microsecond=0)

        total_duration = AgoraCallHistory.objects.filter(
            executive=obj, start_time__gte=start_of_day
        ).aggregate(total_duration=models.Sum('duration'))['total_duration'] or timedelta()

        total_minutes = int(total_duration.total_seconds() // 60)
        target_minutes = 720
        interval_minutes = target_minutes // 4  # 25% intervals = 180 minutes
        coins_per_interval = 10000

        intervals_achieved = total_minutes // interval_minutes

        if total_minutes == 0:
            obj.reward_intervals_today = 0  # Reset reward intervals
            obj.save()

        if not hasattr(obj, "reward_intervals_today"):
            obj.reward_intervals_today = 0
            obj.save()

        current_reward_count = obj.reward_intervals_today
        if intervals_achieved > current_reward_count:
            new_rewards = intervals_achieved - current_reward_count
            total_reward_coins = new_rewards * coins_per_interval

            obj.coins_balance += total_reward_coins
            obj.reward_intervals_today = intervals_achieved
            obj.save()

        progression_percentage = min((total_minutes / target_minutes), 1.0) * 100
        return round(progression_percentage, 2)

    def get_minutes_talked_today(self, obj):
        start_of_day = now().replace(hour=0, minute=0, second=0, microsecond=0)
        total_duration = AgoraCallHistory.objects.filter(
            executive=obj, start_time__gte=start_of_day
        ).aggregate(total_duration=models.Sum('duration'))['total_duration'] or timedelta()
        return int(total_duration.total_seconds() // 60)




from django.utils.timezone import localtime

class TalkTimeHistorySerializer(serializers.ModelSerializer):
    call_history = serializers.SerializerMethodField()
    formatted_duration = serializers.SerializerMethodField()
    coins_deducted = serializers.SerializerMethodField()
    coins_added = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField() 
    is_blocked = serializers.SerializerMethodField() 

    class Meta:
        model = AgoraCallHistory
        fields = [
            'call_history',
            'coins_deducted',
            'coins_added',
            'status',
            'formatted_duration',
            'is_blocked',
        ]

    def get_call_history(self, obj):
        # Handle missing User or Executive safely
        user = getattr(obj, 'user', None)
        executive = getattr(obj, 'executive', None)

        return {
            "id": obj.id,
            "user": {
                "id": user.id if user else None,
                "name": user.name if user else None,
                "mobile_number": user.mobile_number if user else None,
                "coin_balance": user.coin_balance if user else None,
                "user_id": user.user_id if user else None,
                "last_login": user.last_login if user else None,
            } if user else None,
            "executive": {
                "id": executive.id if executive else None,
                "name": executive.name if executive else None,
            } if executive else None,
            "status": obj.status,
            "channel_name": obj.channel_name,
            "executive_joined": obj.executive_joined,
            "call_start_time": localtime(obj.start_time).strftime("%d/%m/%Y %I:%M %p") if obj.start_time else None,
            "call_end_time": localtime(obj.end_time).strftime("%d/%m/%Y %I:%M %p") if obj.end_time else None,
            "duration": obj.duration.total_seconds() if obj.duration else None,
        }

    def get_coins_deducted(self, obj):
        return obj.coins_deducted

    def get_coins_added(self, obj):
        return obj.coins_added

    def get_status(self, obj):
        return obj.status

    def get_formatted_duration(self, obj):
        if obj.duration:
            total_seconds = obj.duration.total_seconds()
            hours, remainder = divmod(int(total_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)

            parts = []
            if hours > 0:
                parts.append(f"{hours} hrs")
            if minutes > 0:
                parts.append(f"{minutes} mins")
            if seconds > 0:
                parts.append(f"{seconds} sec" if seconds == 1 else f"{seconds} secs")

            return " ".join(parts)
        return None

    def get_is_blocked(self, obj):
        from user.models import UserBlock
        user = getattr(obj, 'user', None)
        executive = getattr(obj, 'executive', None)

        if user and executive:
            blocked = UserBlock.objects.filter(user=user, executive=executive, is_blocked=True).exists()
            return blocked
        return False 






class TalkTimeHistoryMinimalSerializer(serializers.ModelSerializer):
    user_id = serializers.SerializerMethodField()
    call_start_time = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()

    class Meta:
        model = TalkTime
        fields = [
            'coins_deducted',
            'user_id',
            'duration',
            'call_start_time',
        ]

    def get_user_id(self, obj):
        return obj.call_history.user.user_id

    def get_call_start_time(self, obj):
        # Format the call start time to exclude milliseconds
        return obj.call_history.start_time.strftime('%Y-%m-%dT%H:%M:%S')  # Format without milliseconds

    def get_duration(self, obj):
        # Format the duration to exclude milliseconds
        total_seconds = int(obj.duration.total_seconds())
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02}:{seconds:02}"

class CoinConversionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinConversion
        fields = ['id', 'coins_earned', 'rupees']


class CallRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallRating
        fields = ['id', 'executive', 'user', 'execallhistory', 'stars', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']

class CallRatingSerializerview(serializers.ModelSerializer):
    executive_name = serializers.CharField(source='executive.name', read_only=True)
    class Meta:
        model = CallRating
        fields = ['id', 'executive', 'user', 'execallhistory','executive_name' ,'stars', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']


class ExecutiveOnCallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Executives
        fields = ['on_call']




class ExecutiveProfilePictureSerializer(serializers.ModelSerializer):
    profile_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = ExecutiveProfilePicture
        fields = ['executive', 'profile_photo_url','profile_photo', 'status', 'created_at', 'updated_at']
        read_only_fields = ['status', 'created_at', 'updated_at']

    def validate_profile_photo(self, value):
        if not value.content_type.startswith('image/'):
            raise serializers.ValidationError("Uploaded file must be an image.")
        max_size = 3 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("Image size must not exceed 5 MB.")
        return value
    
    def get_profile_photo_url(self, obj):
        request = self.context.get('request')
        if obj.profile_photo and request:
            return request.build_absolute_uri(obj.profile_photo.url)
        return None