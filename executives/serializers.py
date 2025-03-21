from rest_framework import serializers
from .models import *
from users.models import *
from calls.models import AgoraCallHistory
from rest_framework_simplejwt.tokens import RefreshToken

class ExecutivesSerializer(serializers.ModelSerializer):
    rating = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    today_talk_time = serializers.SerializerMethodField()
    picked_calls = serializers.SerializerMethodField()
    missed_calls = serializers.SerializerMethodField()
    call_minutes = serializers.SerializerMethodField()
    profile_photo_url = serializers.SerializerMethodField()
    access_token = serializers.SerializerMethodField()
    refresh_token = serializers.SerializerMethodField()
    manager = serializers.SerializerMethodField()
    manager_executive = serializers.PrimaryKeyRelatedField(queryset=Admins.objects.filter(role='manager_executive'), required=False)
    age = serializers.IntegerField(required=True)  # Ensure age is mandatory

    

    class Meta:
        model = Executives
        fields = [
            'id', 'name', 'mobile_number', 'profile_photo_url', 'email_id', 'age', 'online', 'gender',
            'coins_per_second', 'education_qualification', 'profession', 'skills', 'place', 'status',
            'executive_id', 'set_coin', 'duty_start_time', 'total_on_duty_seconds', 'total_talk_seconds_today',
            'total_picked_calls', 'total_missed_calls', 'rating', 'is_favorited', 'password', 'today_talk_time',
            'picked_calls', 'missed_calls', 'is_banned', 'is_suspended', 'call_minutes', 'coins_balance',
            'on_call', 'created_by', 'access_token', 'refresh_token','manager','manager_executive'
        ]
        extra_kwargs = {'password': {'write_only': True}}

    def get_access_token(self, obj):
        refresh = RefreshToken.for_user(obj)
        return str(refresh.access_token)

    def get_refresh_token(self, obj):
        refresh = RefreshToken.for_user(obj)
        return str(refresh)

    def get_today_talk_time(self, obj):
        today = timezone.now().date()
        call_histories = AgoraCallHistory.objects.filter(
            executive=obj, start_time__date=today, status='left'
        )
        total_seconds = sum([ch.duration.total_seconds() for ch in call_histories if ch.duration])
        return total_seconds or 0 
    
    def validate_age(self, value):
        if value is None:
            raise serializers.ValidationError("Age is required.")
        return value

    def get_manager(self, obj):
        return obj.created_by.name if obj.created_by else None

    def get_profile_photo_url(self, obj):
        profile_picture = ExecutiveProfilePicture.objects.filter(executive=obj).first()
        if profile_picture:
            if profile_picture.status == 'approved':
                request = self.context.get('request')
                return request.build_absolute_uri(profile_picture.profile_photo.url) if request else profile_picture.profile_photo.url
            elif profile_picture.status == 'pending':
                return "waiting for approval"
        return None

    def get_picked_calls(self, obj):
        today = timezone.now().date()
        return AgoraCallHistory.objects.filter(executive=obj, start_time__date=today, status='left').count() or 0

    def get_missed_calls(self, obj):
        today = timezone.now().date()
        return AgoraCallHistory.objects.filter(executive=obj, start_time__date=today, status='missed').count() or 0

    def get_rating(self, obj):
        average_rating = obj.call_ratings.aggregate(average_stars=models.Avg('stars'))['average_stars'] or 0.0
        return round(average_rating, 2)

    def get_is_favorited(self, obj):
        user_id = self.context.get('user_id', None)
        if user_id:
            return Favourite.objects.filter(user_id=user_id, executive=obj).exists()
        return False

    def get_call_minutes(self, obj):
        user = self.context.get('user')
        if user and obj.coins_per_second > 0:
            return user.coin_balance // obj.coins_per_second
        return 0

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        instance = super().create(validated_data)
        if password:
            instance.set_password(password)
            instance.save()
        return instance

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save()
        return instance



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
    
class ExecutiveProfilePictureSerializer(serializers.ModelSerializer):
    profile_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = ExecutiveProfilePicture
        fields = ['executive', 'profile_photo_url', 'profile_photo', 'status', 'created_at', 'updated_at']
        read_only_fields = ['status', 'created_at', 'updated_at']

    def validate_profile_photo(self, value):
        if not value.content_type.startswith('image/'):
            raise serializers.ValidationError("Uploaded file must be an image.")
        max_size = 3 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("Image size must not exceed 5 MB.")
        return value
    
    def get_profile_photo_url(self, obj):
        executive = obj.executive  
        
        if executive:
            profile_picture = ExecutiveProfilePicture.objects.filter(executive=executive).first()

            if profile_picture:
                if profile_picture.status == 'approved':
                    request = self.context.get('request')
                    return request.build_absolute_uri(profile_picture.profile_photo.url) if request else profile_picture.profile_photo.url
                elif profile_picture.status == 'pending':
                    return "waiting for approval"

        return None

class GetExecutiveProfilePictureSerializer(serializers.ModelSerializer):
    profile_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = ExecutiveProfilePicture
        fields = ['executive', 'profile_photo_url', 'status', 'created_at', 'updated_at']
        read_only_fields = ['status', 'created_at', 'updated_at']

    def validate_profile_photo(self, value):
        if not value.content_type.startswith('image/'):
            raise serializers.ValidationError("Uploaded file must be an image.")
        max_size = 3 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("Image size must not exceed 5 MB.")
        return value
    
    def get_profile_photo_url(self, obj):
        executive = obj.executive  
        
        if executive:
            profile_picture = ExecutiveProfilePicture.objects.filter(executive=executive).first()

            if profile_picture:
                if profile_picture.status == 'approved':
                    request = self.context.get('request')
                    return request.build_absolute_uri(profile_picture.profile_photo.url) if request else profile_picture.profile_photo.url
                elif profile_picture.status == 'pending':
                    return "waiting for approval"

        return None