from rest_framework import serializers
from .models import *
from django.db.models import Avg
from django.contrib.auth import authenticate
from datetime import datetime
from calls.models import AgoraCallHistory
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import RefreshToken
from executives.models import Executives
from datetime import timedelta
from django.utils import timezone



class AdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    access_token = serializers.SerializerMethodField()
    refresh_token = serializers.SerializerMethodField()

    class Meta:
        model = Admins
        fields = ['id', 'email', 'name', 'password', 'is_staff','mobile_number', 'is_active', 'is_superuser', 'role', 'access_token', 'refresh_token']

    def create(self, validated_data):
        admin = Admins.objects.create(
            email=validated_data['email'],
            name=validated_data['name'],
            mobile_number = validated_data['mobile_number'] ,
            is_staff=validated_data.get('is_staff', False),
            is_active=validated_data.get('is_active', True),
            is_superuser=validated_data.get('is_superuser', False),
            role=validated_data.get('role', 'other')
        )
        admin.set_password(validated_data['password'])
        admin.save()

        return admin

    def get_access_token(self, obj):
        refresh = RefreshToken.for_user(obj)
        return str(refresh.access_token)

    def get_refresh_token(self, obj):
        refresh = RefreshToken.for_user(obj)
        return str(refresh)


class SendOTPSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=15)

    def validate_mobile_number(self, value):
        if not Admins.objects.filter(mobile_number=value).exists():
            raise serializers.ValidationError("No admin found with this mobile number")
        return value


class VerifyOTPSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        mobile_number = attrs['mobile_number']
        otp = attrs['otp']

        try:
            admin = Admins.objects.get(mobile_number=mobile_number)
        except Admins.DoesNotExist:
            raise serializers.ValidationError(
                {"mobile_number": "No admin found with this mobile number"}
            )

        # OTP verification logic
        if not admin.otp or admin.otp != otp:
            admin.otp_attempts += 1
            admin.save()
            raise serializers.ValidationError({"otp": "Invalid OTP"})

        if admin.otp_created_at and (timezone.now() > admin.otp_created_at + timedelta(minutes=5)):
            raise serializers.ValidationError({"otp": "OTP has expired"})

        attrs['admin'] = admin
        return attrs


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
    
class SuperuserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
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

        if not admin.is_active:
            raise serializers.ValidationError("This account is inactive.")

        refresh = RefreshToken.for_user(admin)
        return {
            'id': admin.id,
            'email': admin.email,
            'name': admin.name,
            'role': admin.role,
            'is_superuser': admin.is_superuser,
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh)
        }
    

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

    def create(self, validated_data):
        target_talktime = validated_data.get('target_talktime')
        if isinstance(target_talktime, int):
            validated_data['target_talktime'] = datetime.timedelta(minutes=target_talktime)
        return super().create(validated_data)
    
class ExecutiveStatsSerializer(serializers.ModelSerializer):
    total_online_minutes = serializers.SerializerMethodField()
    total_talktime_minutes = serializers.SerializerMethodField()
    total_accepted_calls = serializers.SerializerMethodField()
    total_missed_calls = serializers.SerializerMethodField()
    coins_balance = serializers.FloatField()
    coins_earned_today = serializers.SerializerMethodField()
    bonus_coins_earned_today = serializers.SerializerMethodField()
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
            'bonus_coins_earned_today', 
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

    def calculate_bonus_coins(self, obj):
        start_of_day = now().replace(hour=0, minute=0, second=0, microsecond=0)
        total_duration = AgoraCallHistory.objects.filter(
            executive=obj, start_time__gte=start_of_day
        ).aggregate(total_duration=models.Sum('duration'))['total_duration'] or timedelta()

        total_minutes = int(total_duration.total_seconds() // 60)

        reward_tiers = [
            (180, 5000),     # 3 hours
            (360, 7500),     # 6 hours
            (540, 10000),    # 9 hours
            (720, 15000),    # 12 hours
        ]

        if not hasattr(obj, "reward_intervals_today"):
            obj.reward_intervals_today = 0 
            obj.save()

        coins_to_add = 0
        tiers_completed = 0

        for minutes_required, coins in reward_tiers:
            if total_minutes >= minutes_required:
                tiers_completed += 1
            else:
                break

        if tiers_completed > obj.reward_intervals_today:
            for i in range(obj.reward_intervals_today, tiers_completed):
                coins_to_add += reward_tiers[i][1]

            obj.coins_balance += coins_to_add
            obj.reward_intervals_today = tiers_completed
            obj.save()

        return coins_to_add, total_minutes

    def get_progression_percentage(self, obj):
        _, total_minutes = self.calculate_bonus_coins(obj)
        return round(min((total_minutes / 720), 1.0) * 100, 2)

    def get_bonus_coins_earned_today(self, obj):
        coins_to_add, _ = self.calculate_bonus_coins(obj)
        return coins_to_add

    def get_minutes_talked_today(self, obj):
        start_of_day = now().replace(hour=0, minute=0, second=0, microsecond=0)
        total_duration = AgoraCallHistory.objects.filter(
            executive=obj, start_time__gte=start_of_day
        ).aggregate(total_duration=models.Sum('duration'))['total_duration'] or timedelta()
        return int(total_duration.total_seconds() // 60)

