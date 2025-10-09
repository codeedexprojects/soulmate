from rest_framework import serializers
from .models import *
from executives.models import Executives, ExecutiveProfilePicture
import random
from .utils import send_otp_2factor
from django.conf import settings


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'mobile_number', 'otp', 'gender', 'coin_balance', 'user_id', 'last_login','is_deleted']
        read_only_fields = ['user_id', 'last_login', 'otp']

    def create(self, validated_data):
        otp = str(random.randint(100000, 999999))
        validated_data['otp'] = otp

        send_otp_2factor(validated_data['mobile_number'], otp)

        return User.objects.create(**validated_data)
    
class FavouriteSerializer(serializers.ModelSerializer):
    executive_id = serializers.IntegerField(source='executive.id', read_only=True)
    executive_name = serializers.CharField(source='executive.name', read_only=True)
    executive_gender = serializers.CharField(source='executive.gender', read_only=True)
    executive_mobile_number = serializers.CharField(source='executive.mobile_number', read_only=True)
    executive_email_id = serializers.EmailField(source='executive.email_id', read_only=True)
    executive_age = serializers.IntegerField(source='executive.age', read_only=True)
    executive_online = serializers.BooleanField(source='executive.online', read_only=True)
    executive_on_call = serializers.BooleanField(source='executive.on_call', read_only=True)
    executive_coins_per_second = serializers.FloatField(source='executive.coins_per_second', read_only=True)
    executive_education_qualification = serializers.CharField(source='executive.education_qualification', read_only=True)
    executive_profession = serializers.CharField(source='executive.profession', read_only=True)
    executive_skills = serializers.CharField(source='executive.skills', read_only=True)
    executive_place = serializers.CharField(source='executive.place', read_only=True)
    executive_status = serializers.CharField(source='executive.status', read_only=True)
    executive_executive_id = serializers.CharField(source='executive.executive_id', read_only=True)
    executive_set_coin = serializers.DecimalField(source='executive.set_coin', max_digits=10, decimal_places=2, read_only=True)
    executive_coins_balance = serializers.IntegerField(source='executive.coins_balance', read_only=True)
    executive_total_on_duty_seconds = serializers.IntegerField(source='executive.total_on_duty_seconds', read_only=True)
    executive_total_talk_seconds_today = serializers.IntegerField(source='executive.total_talk_seconds_today', read_only=True)
    executive_total_picked_calls = serializers.IntegerField(source='executive.total_picked_calls', read_only=True)
    executive_total_missed_calls = serializers.IntegerField(source='executive.total_missed_calls', read_only=True)
    executive_is_banned = serializers.BooleanField(source='executive.is_banned', read_only=True)
    executive_is_suspended = serializers.BooleanField(source='executive.is_suspended', read_only=True)
    executive_profile_photo = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = Favourite
        fields = [
            'user',
            'executive',
            'executive_id',
            'executive_name',
            'executive_gender',
            'executive_mobile_number',
            'executive_email_id',
            'executive_age',
            'executive_online',
            'executive_on_call',
            'executive_coins_per_second',
            'executive_education_qualification',
            'executive_profession',
            'executive_skills',
            'executive_place',
            'executive_status',
            'executive_executive_id',
            'executive_set_coin',
            'executive_coins_balance',
            'executive_total_on_duty_seconds',
            'executive_total_talk_seconds_today',
            'executive_total_picked_calls',
            'executive_total_missed_calls',
            'executive_is_banned',
            'executive_is_suspended',
            'created_at',
            'executive_profile_photo', 
            'is_favorited'
        ]

    def get_is_favorited(self, obj):
        return True
    
    def get_executive_profile_photo(self, obj):
        try:
            picture = ExecutiveProfilePicture.objects.get(executive=obj.executive, status='approved')
            if picture.profile_photo:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(picture.profile_photo.url)
                return picture.profile_photo.url
        except ExecutiveProfilePicture.DoesNotExist:
            return None
    
class RatingSerializer(serializers.ModelSerializer):
    executive = serializers.PrimaryKeyRelatedField(queryset=Executives.objects.all())

    class Meta:
        model = Rating
        fields = ['user', 'executive', 'comment','rating', 'created_at']

    def validate_executive(self, value):
        return value
    
class ExecutiveSerializer(serializers.ModelSerializer):
    is_favorited = serializers.SerializerMethodField()
    executive_profile_photo = serializers.SerializerMethodField()

    class Meta:
        model = Executives
        fields = ['id', 'name', 'is_favorited','executive_profile_photo']

    def get_is_favorited(self, executive):
        user_id = self.context.get('user_id')
        if user_id:
            return Favourite.objects.filter(user_id=user_id, executive=executive).exists()
        return False
    
    def get_executive_profile_photo(self, executive):
        try:
            # Get the approved profile picture for the executive
            profile_picture = ExecutiveProfilePicture.objects.get(executive=executive, status='approved')
            request = self.context.get('request')
            if request:
                # Return absolute URL
                return request.build_absolute_uri(profile_picture.profile_photo.url)
            return profile_picture.profile_photo.url
        except ExecutiveProfilePicture.DoesNotExist:
            return None

    
class UserProfileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.name', read_only=True)
    gender = serializers.CharField(source='user.gender', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'coin_balance', 'name', 'gender']

class CarouselImageSerializer(serializers.ModelSerializer):
    full_image_url = serializers.SerializerMethodField()

    class Meta:
        model = CarouselImage
        fields = ['id', 'title', 'image', 'full_image_url', 'created_at']

    def get_full_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            url = request.build_absolute_uri(obj.image.url)
            return url.replace("http://", "https://", 1)
        return None


class CareerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Career
        fields = '__all__'

class UserMaxCallTimeSerializer(serializers.ModelSerializer):
    max_call_time_minutes = serializers.SerializerMethodField()
    max_call_time_seconds = serializers.SerializerMethodField()
    limit_call_time_minutes = serializers.SerializerMethodField()
    limit_call_time_seconds = serializers.SerializerMethodField()
    call_end_warning = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField() 

    class Meta:
        model = User
        fields = [
            'id',
            'name',
            'mobile_number',
            'coin_balance',
            'user_id',
            'max_call_time_minutes',
            'max_call_time_seconds',
            'limit_call_time_minutes',
            'limit_call_time_seconds',
            'call_end_warning',
            'time', 
        ]

    def get_max_call_time_minutes(self, obj):
        max_seconds = self._get_max_call_time_seconds(obj)
        return max_seconds // 60

    def get_limit_call_time_minutes(self, obj):
        limit_seconds = self.get_limit_call_time_seconds(obj)
        return limit_seconds // 60

    def get_max_call_time_seconds(self, obj):
        return self._get_max_call_time_seconds(obj)

    def get_limit_call_time_seconds(self, obj):
        return 60

    def get_call_end_warning(self, obj):
        return self._get_max_call_time_seconds(obj) < self.get_limit_call_time_seconds(obj)

    def get_time(self, obj):
        max_seconds = self._get_max_call_time_seconds(obj)
        minutes = max_seconds // 60
        seconds = max_seconds % 60
        return f"{minutes} minutes and {seconds} seconds"

    def _get_max_call_time_seconds(self, obj):
        rate_per_second = 3  
        if obj.coin_balance is not None and obj.coin_balance > 0:
            return obj.coin_balance // rate_per_second
        return 0

class ExecutiveMaxCallTimeSerializer(serializers.ModelSerializer):
    max_call_time_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Executives
        fields = ['id', 'name', 'coin_per_minute', 'max_call_time_minutes']

    def get_max_call_time_minutes(self, obj):
        user_coin_balance = self.context.get('coin_balance', 0)
        if obj.coins_per_second > 0:
            return user_coin_balance // obj.coins_per_second
        return 0
    
class ReferralCodeSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    name = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = ReferralCode
        fields = ['user_id', 'name', 'code']

class UserBlockSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source='user.user_id', read_only=True)
    executive_id = serializers.CharField(source='executive.executive_id', read_only=True) 

    class Meta:
        model = UserBlock
        fields = ['id', 'user_id', 'executive_id', 'is_blocked', 'reason', 'blocked_at']


class UserBlockListSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source='user.user_id', read_only=True)
    executive_id = serializers.CharField(source='executive.executive_id', read_only=True)
    blocked_at = serializers.DateTimeField(format="%d %b %Y, %H:%M") 

    class Meta:
        model = UserBlock
        fields = '__all__'

class UserDPImageSerializer(serializers.ModelSerializer):
    dp_image = serializers.ImageField(required=False)  

    class Meta:
        model = User
        fields = ['dp_image']


class ReferredUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name']

class ReferralHistorySerializer(serializers.ModelSerializer):
    referred_user = ReferredUserSerializer()
    referral_amount = serializers.SerializerMethodField()
    referred_user_id = serializers.CharField(source='referred_user.user_id',read_only=True)
    referrer_user_id = serializers.CharField(source='referrer.user_id',read_only=True)
    class Meta:
        model = ReferralHistory
        fields = ['referred_user', 'referral_amount','referrer','referrer_user_id','referred_user_id']

    def get_referral_amount(self, obj):
        return 1000  

class ReferralDetailHistorySerializer(serializers.ModelSerializer):
    referred_user = ReferredUserSerializer()
    referral_amount = serializers.SerializerMethodField()
    referrer_name = serializers.CharField(source='referrer.name',read_only=True)
    referrer_mobile = serializers.CharField(source='referrer.mobile_number',read_only=True)
    referred_user_mobile = serializers.CharField(source='referred_user.mobile_number',read_only=True)
    referred_user_id = serializers.CharField(source='referred_user.user_id',read_only=True)
    referrer_user_id = serializers.CharField(source='referrer.user_id',read_only=True)

    class Meta:
        model = ReferralHistory
        fields = ['referred_user', 'referral_amount','referrer','referrer_name','referrer_mobile','referred_user_mobile','referrer_user_id','referred_user_id']

    def get_referral_amount(self, obj):
        return 1000  

class BannedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'mobile_number', 'user_id', 'is_banned']