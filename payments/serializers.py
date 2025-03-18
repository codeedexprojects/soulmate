from rest_framework import serializers
from .models import *
from analytics.models import CoinRedemptionRequest

class RechargePlanSerializer(serializers.ModelSerializer):
    discount_amount = serializers.SerializerMethodField()
    final_amount = serializers.SerializerMethodField()
    total_talktime = serializers.SerializerMethodField()
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
            'category_id', 'category_name', 'total_talktime'
        ]

    def get_discount_amount(self, obj):
        return obj.calculate_discount()

    def get_final_amount(self, obj):
        return obj.calculate_final_price()

    def get_total_talktime(self, obj):
        talktime_minutes = obj.coin_package / 180 
        return f"Your plan talktime is upto {talktime_minutes:.0f} minutes"  
    
class CategoryWithPlansSerializer(serializers.ModelSerializer):
    plans = serializers.SerializerMethodField()

    class Meta:
        model = RechargePlanCato
        fields = ['id', 'name', 'plans']

    def get_plans(self, obj):
        plans = obj.recharge_plans.all()
        return RechargePlanSerializer(plans, many=True).data
    
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


class CoinRedemptionRequestSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='executive.name', read_only=True)

    class Meta:
        model = CoinRedemptionRequest
        fields = ['id', 'executive','name', 'amount_requested', 'upi_id', 'request_time', 'status','created_at']
        read_only_fields = ['executive', 'amount_requested', 'created_at', 'status']