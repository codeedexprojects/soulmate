from django.contrib import admin
from .models import RechargePlanCato, RechargePlan, Sale, PurchaseHistories, CoinConversion, PaymentTransaction


@admin.register(RechargePlanCato)
class RechargePlanCatoAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    actions = ['activate_categories', 'deactivate_categories']
    
    def activate_categories(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} category(ies) activated.')
    activate_categories.short_description = "Activate selected categories"
    
    def deactivate_categories(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} category(ies) deactivated.')
    deactivate_categories.short_description = "Deactivate selected categories"


@admin.register(RechargePlan)
class RechargePlanAdmin(admin.ModelAdmin):
    list_display = ('plan_name', 'coin_package', 'base_price', 'discount_percentage', 'get_final_price', 'category_id', 'is_active')
    list_filter = ('is_active', 'category_id', 'discount_percentage')
    search_fields = ('plan_name', 'category_id__name')
    readonly_fields = ('calculate_final_price', 'calculate_discount', 'calculate_talk_time_minutes', 'get_adjusted_coin_package')
    ordering = ('-id',)
    
    fieldsets = (
        ('Plan Information', {
            'fields': ('plan_name', 'category_id', 'total_talktime')
        }),
        ('Pricing', {
            'fields': ('coin_package', 'base_price', 'discount_percentage', 'calculate_discount', 'calculate_final_price')
        }),
        ('Calculations', {
            'fields': ('calculate_talk_time_minutes', 'get_adjusted_coin_package'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    actions = ['activate_plans', 'deactivate_plans']
    
    def activate_plans(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} plan(s) activated.')
    activate_plans.short_description = "Activate selected plans"
    
    def deactivate_plans(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} plan(s) deactivated.')
    deactivate_plans.short_description = "Deactivate selected plans"
    
    def get_final_price(self, obj):
        return f"₹{obj.calculate_final_price()}"
    get_final_price.short_description = 'Final Price'


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('package', 'amount', 'created_at')
    list_filter = ('package', 'created_at')
    search_fields = ('package__plan_name',)
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Sale Information', {
            'fields': ('package', 'amount')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(PurchaseHistories)
class PurchaseHistoriesAdmin(admin.ModelAdmin):
    list_display = ('user', 'recharge_plan', 'coins_purchased', 'purchased_price', 'payment_status', 'is_admin', 'purchase_date')
    list_filter = ('payment_status', 'is_admin', 'purchase_date', 'recharge_plan')
    search_fields = ('user__name', 'user__mobile_number', 'user__email', 'razorpay_order_id', 'razorpay_payment_id')
    readonly_fields = ('purchase_date', 'created_at', 'razorpay_order_id', 'razorpay_payment_id')
    ordering = ('-purchase_date',)
    
    fieldsets = (
        ('User & Plan', {
            'fields': ('user', 'recharge_plan', 'is_admin')
        }),
        ('Purchase Details', {
            'fields': ('coins_purchased', 'purchased_price', 'purchase_date')
        }),
        ('Payment Information', {
            'fields': ('razorpay_order_id', 'razorpay_payment_id', 'payment_status')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_pending', 'mark_as_success', 'mark_as_failed']
    
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(payment_status='PENDING')
        self.message_user(request, f'{updated} purchase(es) marked as pending.')
    mark_as_pending.short_description = "Mark as Pending"
    
    def mark_as_success(self, request, queryset):
        updated = queryset.update(payment_status='SUCCESS')
        self.message_user(request, f'{updated} purchase(es) marked as successful.')
    mark_as_success.short_description = "Mark as Success"
    
    def mark_as_failed(self, request, queryset):
        updated = queryset.update(payment_status='FAILED')
        self.message_user(request, f'{updated} purchase(es) marked as failed.')
    mark_as_failed.short_description = "Mark as Failed"


@admin.register(CoinConversion)
class CoinConversionAdmin(admin.ModelAdmin):
    list_display = ('coins_earned', 'rupees', 'get_conversion_rate')
    search_fields = ('coins_earned', 'rupees')
    
    def get_conversion_rate(self, obj):
        if obj.coins_earned and obj.rupees:
            rate = obj.rupees / obj.coins_earned
            return f"₹{rate:.4f} per coin"
        return "N/A"
    get_conversion_rate.short_description = 'Conversion Rate'


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'amount', 'status', 'payment_mode', 'created_at')
    list_filter = ('status', 'payment_mode', 'created_at')
    search_fields = ('order_id', 'cf_order_id', 'user__name', 'user__email', 'user__mobile_number', 'transaction_id')
    readonly_fields = ('created_at', 'order_id', 'cf_order_id', 'signature')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('order_id', 'cf_order_id', 'user', 'amount')
        }),
        ('Payment Information', {
            'fields': ('status', 'payment_mode', 'transaction_id')
        }),
        ('Verification', {
            'fields': ('signature',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_pending', 'mark_as_success', 'mark_as_failed']
    
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(status='PENDING')
        self.message_user(request, f'{updated} transaction(s) marked as pending.')
    mark_as_pending.short_description = "Mark as Pending"
    
    def mark_as_success(self, request, queryset):
        updated = queryset.update(status='SUCCESS')
        self.message_user(request, f'{updated} transaction(s) marked as successful.')
    mark_as_success.short_description = "Mark as Success"
    
    def mark_as_failed(self, request, queryset):
        updated = queryset.update(status='FAILED')
        self.message_user(request, f'{updated} transaction(s) marked as failed.')
    mark_as_failed.short_description = "Mark as Failed"
