from django.contrib import admin
from .models import Executives, BlockedDevices, ExecutiveProfilePicture, LoginActivity


@admin.register(Executives)
class ExecutivesAdmin(admin.ModelAdmin):
    list_display = ('executive_id', 'name', 'mobile_number', 'email_id', 'gender', 'age', 'status', 'online', 'coins_balance', 'is_banned', 'is_suspended', 'created_at')
    list_filter = ('gender', 'status', 'online', 'is_banned', 'is_suspended', 'is_verified', 'created_at')
    search_fields = ('name', 'mobile_number', 'email_id', 'executive_id', 'place')
    readonly_fields = ('executive_id', 'created_at', 'last_login', 'last_activity')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('executive_id', 'name', 'mobile_number', 'email_id', 'age', 'gender', 'place')
        }),
        ('Professional Information', {
            'fields': ('education_qualification', 'profession', 'skills')
        }),
        ('Banking Information', {
            'fields': ('account_number', 'ifsc_code')
        }),
        ('Account Status', {
            'fields': ('status', 'online', 'is_banned', 'is_suspended', 'is_verified')
        }),
        ('Coin Management', {
            'fields': ('coins_balance', 'coins_per_second', 'set_coin')
        }),
        ('Duty & Activity', {
            'fields': ('duty_start_time', 'total_on_duty_seconds', 'total_talk_seconds_today', 'last_activity')
        }),
        ('Call Statistics', {
            'fields': ('total_picked_calls', 'total_missed_calls', 'on_call')
        }),
        ('Device & Session', {
            'fields': ('device_id', 'fcm_token', 'current_session_key', 'is_logged_out', 'last_login')
        }),
        ('Management', {
            'fields': ('user_id', 'manager_executive')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['ban_executives', 'unban_executives', 'suspend_executives', 'unsuspend_executives', 'mark_as_active', 'mark_as_inactive', 'set_online', 'set_offline']
    
    def ban_executives(self, request, queryset):
        updated = queryset.update(is_banned=True)
        self.message_user(request, f'{updated} executive(s) banned.')
    ban_executives.short_description = "Ban selected executives"
    
    def unban_executives(self, request, queryset):
        updated = queryset.update(is_banned=False)
        self.message_user(request, f'{updated} executive(s) unbanned.')
    unban_executives.short_description = "Unban selected executives"
    
    def suspend_executives(self, request, queryset):
        updated = queryset.update(is_suspended=True)
        self.message_user(request, f'{updated} executive(s) suspended.')
    suspend_executives.short_description = "Suspend selected executives"
    
    def unsuspend_executives(self, request, queryset):
        updated = queryset.update(is_suspended=False)
        self.message_user(request, f'{updated} executive(s) unsuspended.')
    unsuspend_executives.short_description = "Unsuspend selected executives"
    
    def mark_as_active(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} executive(s) marked as active.')
    mark_as_active.short_description = "Mark selected executives as active"
    
    def mark_as_inactive(self, request, queryset):
        updated = queryset.update(status='inactive')
        self.message_user(request, f'{updated} executive(s) marked as inactive.')
    mark_as_inactive.short_description = "Mark selected executives as inactive"
    
    def set_online(self, request, queryset):
        updated = queryset.update(online=True)
        self.message_user(request, f'{updated} executive(s) set to online.')
    set_online.short_description = "Set selected executives as online"
    
    def set_offline(self, request, queryset):
        updated = queryset.update(online=False)
        self.message_user(request, f'{updated} executive(s) set to offline.')
    set_offline.short_description = "Set selected executives as offline"


@admin.register(BlockedDevices)
class BlockedDevicesAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'is_banned')
    list_filter = ('is_banned',)
    search_fields = ('device_id',)
    
    actions = ['block_devices', 'unblock_devices']
    
    def block_devices(self, request, queryset):
        updated = queryset.update(is_banned=True)
        self.message_user(request, f'{updated} device(s) blocked.')
    block_devices.short_description = "Block selected devices"
    
    def unblock_devices(self, request, queryset):
        updated = queryset.update(is_banned=False)
        self.message_user(request, f'{updated} device(s) unblocked.')
    unblock_devices.short_description = "Unblock selected devices"


@admin.register(ExecutiveProfilePicture)
class ExecutiveProfilePictureAdmin(admin.ModelAdmin):
    list_display = ('executive', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at', 'updated_at')
    search_fields = ('executive__name', 'executive__mobile_number')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Profile Picture', {
            'fields': ('executive', 'profile_photo', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_pictures', 'reject_pictures']
    
    def approve_pictures(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f'{updated} profile picture(s) approved.')
    approve_pictures.short_description = "Approve selected pictures"
    
    def reject_pictures(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} profile picture(s) rejected.')
    reject_pictures.short_description = "Reject selected pictures"


@admin.register(LoginActivity)
class LoginActivityAdmin(admin.ModelAdmin):
    list_display = ('executive', 'timestamp', 'device_id', 'ip_address')
    list_filter = ('timestamp', 'executive')
    search_fields = ('executive__name', 'executive__mobile_number', 'device_id', 'ip_address')
    readonly_fields = ('timestamp', 'executive', 'device_id', 'ip_address', 'user_agent')
    ordering = ('-timestamp',)
    
    fieldsets = (
        ('Login Information', {
            'fields': ('executive', 'timestamp', 'device_id', 'ip_address')
        }),
        ('User Agent', {
            'fields': ('user_agent',),
            'classes': ('collapse',)
        }),
    )
