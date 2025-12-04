# # analytics/admin.py

# from django.contrib import admin
# from .models import Admins, CoinRedemptionRequest, RevenueTarget

# # ✅ CORRECT - Register ONCE, not twice
# @admin.register(Admins)
# class AdminModelAdmin(admin.ModelAdmin):
#     list_display = ('email', 'name', 'role', 'is_active', 'created_at')
#     list_filter = ('role', 'is_active', 'created_at')
#     search_fields = ('email', 'name', 'mobile_number')
#     ordering = ('-created_at',)
    
#     fieldsets = (
#         ('Personal Info', {
#             'fields': ('email', 'name', 'mobile_number')
#         }),
#         ('Status', {
#             'fields': ('is_active', 'is_staff', 'is_superuser', 'is_banned')
#         }),
#         ('Role & Permissions', {
#             'fields': ('role', 'groups', 'user_permissions')
#         }),
#         ('OTP', {
#             'fields': ('otp', 'otp_created_at', 'otp_attempts', 'otp_verified_at')
#         }),
#         ('Dates', {
#             'fields': ('created_at',)
#         }),
#     )

# @admin.register(CoinRedemptionRequest)
# class CoinRedemptionRequestAdmin(admin.ModelAdmin):
#     list_display = ('executive', 'amount_requested', 'status', 'request_time')
#     list_filter = ('status', 'request_time')

# @admin.register(RevenueTarget)
# class RevenueTargetAdmin(admin.ModelAdmin):
#     list_display = ('target_revenue', 'target_talktime', 'created_at')
