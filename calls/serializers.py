from rest_framework import serializers
from .models import *
from users.serializers import UserSerializer,ExecutiveSerializer
from django.utils.timezone import localtime
from payments.models import CoinConversion

class   CallHistorySerializer(serializers.ModelSerializer):
    user = UserSerializer()
    executive = ExecutiveSerializer()
    formatted_duration = serializers.SerializerMethodField()
    formatted_start_time = serializers.SerializerMethodField()
    formatted_end_time = serializers.SerializerMethodField()
    executive_gender = serializers.SerializerMethodField()
    duration_seconds = serializers.SerializerMethodField() 
    duration_minutes_seconds = serializers.SerializerMethodField()  
    duration_hours_minutes_seconds = serializers.SerializerMethodField() 

    class Meta:
        model = AgoraCallHistory
        fields = [
            'id', 
            'user',
            'executive',
            'executive_gender',
            'duration',
            'status',
            'formatted_duration',
            'formatted_start_time',
            'formatted_end_time',
            'start_time',
            'end_time',
            'duration_seconds',
            'duration_minutes_seconds',
            'duration_hours_minutes_seconds',
        ]

    def get_formatted_duration(self, obj):
        duration = obj.duration
        if duration is None:
            return None
        total_seconds = int(duration.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s" if seconds > 0 else f"{minutes}m"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"

    def get_duration_seconds(self, obj):
        duration = obj.duration
        return int(duration.total_seconds()) if duration else None

    def get_duration_minutes_seconds(self, obj):
        duration = obj.duration
        if not duration:
            return None
        total_seconds = int(duration.total_seconds())
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s" if seconds > 0 else f"{minutes}m"

    def get_duration_hours_minutes_seconds(self, obj):
        duration = obj.duration
        if not duration:
            return None
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            if minutes > 0 and seconds > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{hours}h"
        elif minutes > 0:
            return f"{minutes}m {seconds}s" if seconds > 0 else f"{minutes}m"
        else:
            return f"{seconds}s"

    def get_formatted_start_time(self, obj):
        if obj.start_time is None:
            return None
        return obj.start_time.strftime('%B %d, %Y, %I:%M %p')

    def get_formatted_end_time(self, obj):
        if obj.end_time is None:
            return None
        return obj.end_time.strftime('%B %d, %Y, %I:%M %p')

    def get_executive_gender(self, obj):
        return obj.executive.gender
    
class ExeCallHistorySerializer(serializers.ModelSerializer):
    call_date = serializers.SerializerMethodField()

    class Meta:
        model = AgoraCallHistory
        fields = ['executive', 'call_duration', 'coins_earned', 'call_date']

    def get_call_date(self, obj):
        return obj.call_date.strftime("%a, %d %b %I:%M %p")
    
class CallHistoryRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallRating
        fields = ['id', 'stars','comment']

    def validate_rating(self, value):
        if not (0 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 0 and 5.")
        return value
    
class ExecutiveCallHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AgoraCallHistory
        fields = ['id','executive', 'status', 'start_time', 'end_time']

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
                "gender": executive.gender if executive else None,
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
        from users.models import UserBlock
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
        return obj.call_history.start_time.strftime('%Y-%m-%dT%H:%M:%S')  

    def get_duration(self, obj):
        total_seconds = int(obj.duration.total_seconds())
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02}:{seconds:02}"
    
class CoinConversionSerializer(serializers.ModelSerializer):
    rupees = serializers.SerializerMethodField()

    class Meta:
        model = CoinConversion
        fields = ['id', 'coins_earned', 'rupees']

    def get_rupees(self, obj):
        return float(obj.rupees)


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
    on_call = serializers.BooleanField()  

    class Meta:
        model = Executives
        fields = ['on_call']