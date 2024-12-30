from rest_framework import serializers
from .models import *
from executive.models import Executives
import random
from .utils import send_otp_2factor
from django.conf import settings


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'mobile_number', 'otp', 'is_verified', 'gender', 'coin_balance', 'user_id', 'last_login']
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
            'is_favorited'
        ]

    def get_is_favorited(self, obj):
        return True



class RatingSerializer(serializers.ModelSerializer):
    executive = serializers.PrimaryKeyRelatedField(queryset=Executives.objects.all())

    class Meta:
        model = Rating
        fields = ['user', 'executive', 'comment','rating', 'created_at']

    def validate_executive(self, value):
        return value


class ExecutiveSerializer(serializers.ModelSerializer):
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = Executives
        fields = ['id', 'name', 'is_favorited']

    def get_is_favorited(self, executive):
        user_id = self.context.get('user_id')
        if user_id:
            return Favourite.objects.filter(user_id=user_id, executive=executive).exists()
        return False


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
        """Returns a user-friendly duration (e.g., Xm Ys, Xh Ym)."""
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



class RechargePlanSerializer(serializers.ModelSerializer):
    discount_amount = serializers.SerializerMethodField()
    final_amount = serializers.SerializerMethodField()
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=RechargePlanCato.objects.all(),  
        write_only=True
    )
    category_name = serializers.CharField(
        source='category_id.name',  
        read_only=True
    )

    class Meta:
        model = RechargePlan
        fields = [
            'id', 'plan_name', 'coin_package', 'base_price',
            'discount_percentage', 'discount_amount', 'final_amount',
            'category_id', 'category_name'
        ]

    def get_discount_amount(self, obj):
        return obj.calculate_discount()

    def get_final_amount(self, obj):
        return obj.calculate_final_price()



class CategoryWithPlansSerializer(serializers.ModelSerializer):
    plans = serializers.SerializerMethodField()

    class Meta:
        model = RechargePlanCato
        fields = ['id', 'name', 'plans']

    def get_plans(self, obj):
        plans = obj.recharge_plans.all()
        return RechargePlanSerializer(plans, many=True).data



class UserProfileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.name', read_only=True)
    gender = serializers.CharField(source='user.gender', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'coin_balance', 'name', 'gender']


class RechargeCoinsSerializer(serializers.Serializer):
    coin_package = serializers.IntegerField()
    base_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = serializers.FloatField(required=False, default=0)

    def validate(self, data):
        if data['coin_package'] <= 0:
            raise serializers.ValidationError("Coin package must be a positive number.")
        if data['base_amount'] <= 0:
            raise serializers.ValidationError("Base amount must be a positive number.")
        if not (0 <= data['discount_percentage'] <= 100):
            raise serializers.ValidationError("Discount percentage must be between 0 and 100.")
        return data

    def calculate_discount(self, base_amount, discount_percentage):
        return base_amount * (discount_percentage / 100)

    def calculate_final_amount(self, base_amount, discount):
        return base_amount - discount

    def create(self, validated_data):
        coin_package = validated_data['coin_package']
        base_amount = validated_data['base_amount']
        discount_percentage = validated_data['discount_percentage']

        discount = self.calculate_discount(base_amount, discount_percentage)
        final_amount = self.calculate_final_amount(base_amount, discount)

        return {
            'coin_package': coin_package,
            'base_amount': base_amount,
            'discount_percentage': discount_percentage,
            'discount_amount': discount,
            'final_amount': final_amount
        }


class CarouselImageSerializer(serializers.ModelSerializer):
    full_image_url = serializers.SerializerMethodField()

    class Meta:
        model = CarouselImage
        fields = ['id', 'title', 'image', 'full_image_url', 'created_at']

    def get_full_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None


class CareerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Career
        fields = '__all__'


class PurchaseHistorySerializer(serializers.ModelSerializer):
    base_price = serializers.CharField(source='recharge_plan.base_price', read_only=True)
    final_amount = serializers.SerializerMethodField()
    purchase_date = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseHistory
        fields = ['id', 'recharge_plan', 'coins_purchased', 'purchased_price', 'base_price', 'final_amount', 'purchase_date']

    def get_final_amount(self, obj):
        return obj.recharge_plan.calculate_final_price()

    def get_purchase_date(self, obj):
        return obj.purchase_date.strftime("%a, %d %b %I:%M %p")


class RechargePlanCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RechargePlanCato
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
    user_id = serializers.CharField(source='user.user_id', read_only=True)  # Display custom user_id
    executive_id = serializers.CharField(source='executive.executive_id', read_only=True)  # Display custom executive_id

    class Meta:
        model = UserBlock
        fields = ['id', 'user_id', 'executive_id', 'is_blocked', 'reason', 'blocked_at']


class UserBlockListSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source='user.user_id', read_only=True)  # Display custom user_id
    executive_id = serializers.CharField(source='executive.executive_id', read_only=True)  # Display custom executive_id
    user_name = serializers.CharField(source='user.name', read_only=True)  # Display user name
    executive_name = serializers.CharField(source='executive.name', read_only=True)  # Display executive name

    class Meta:
        model = UserBlock
        fields = ['id', 'user_id', 'user_name', 'executive_id', 'executive_name', 'is_blocked', 'reason', 'blocked_at']

