from django.contrib import admin
from .models import AgoraCallHistory, Channel, CallRating, TalkTime


@admin.register(AgoraCallHistory)
class AgoraCallHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'executive', 'channel_name', 'status', 'start_time', 'duration', 'coins_deducted', 'coins_added', 'is_active')
    list_filter = ('status', 'start_time', 'executive_joined', 'is_active', 'cleared_by_user')
    search_fields = ('user__name', 'user__mobile_number', 'executive__name', 'executive__mobile_number', 'channel_name')
    readonly_fields = ('start_time', 'duration', 'end_time', 'uid')
    ordering = ('-start_time',)
    fieldsets = (
        ('Call Participants', {
            'fields': ('user', 'executive', 'channel_name')
        }),
        ('Call Details', {
            'fields': ('status', 'start_time', 'end_time', 'duration', 'uid', 'is_active')
        }),
        ('Tokens', {
            'fields': ('token', 'executive_token'),
            'classes': ('collapse',)
        }),
        ('Coin Transfer', {
            'fields': ('coins_deducted', 'coins_added', 'last_coin_update_time')
        }),
        ('Status Flags', {
            'fields': ('executive_joined', 'cleared_by_user'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_completed', 'mark_as_missed', 'mark_as_rejected']
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='left')
        self.message_user(request, f'{updated} call(s) marked as completed.')
    mark_as_completed.short_description = "Mark selected calls as completed"
    
    def mark_as_missed(self, request, queryset):
        updated = queryset.update(status='missed')
        self.message_user(request, f'{updated} call(s) marked as missed.')
    mark_as_missed.short_description = "Mark selected calls as missed"
    
    def mark_as_rejected(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} call(s) marked as rejected.')
    mark_as_rejected.short_description = "Mark selected calls as rejected"


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at', 'updated_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    fieldsets = (
        ('Channel Information', {
            'fields': ('name', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_active', 'mark_as_ended', 'mark_as_expired']
    
    def mark_as_active(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} channel(s) marked as active.')
    mark_as_active.short_description = "Mark selected channels as active"
    
    def mark_as_ended(self, request, queryset):
        updated = queryset.update(status='ended')
        self.message_user(request, f'{updated} channel(s) marked as ended.')
    mark_as_ended.short_description = "Mark selected channels as ended"
    
    def mark_as_expired(self, request, queryset):
        updated = queryset.update(status='expired')
        self.message_user(request, f'{updated} channel(s) marked as expired.')
    mark_as_expired.short_description = "Mark selected channels as expired"


@admin.register(CallRating)
class CallRatingAdmin(admin.ModelAdmin):
    list_display = ('executive', 'user', 'stars', 'created_at')
    list_filter = ('stars', 'created_at', 'executive')
    search_fields = ('executive__name', 'user__name', 'executive__mobile_number', 'user__mobile_number')
    readonly_fields = ('created_at', 'execallhistory')
    ordering = ('-created_at',)
    fieldsets = (
        ('Rating Details', {
            'fields': ('executive', 'user', 'execallhistory', 'stars', 'comment')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(TalkTime)
class TalkTimeAdmin(admin.ModelAdmin):
    list_display = ('call_history', 'get_user', 'get_executive')
    list_filter = ('call_history__start_time',)
    search_fields = ('call_history__user__name', 'call_history__executive__name')
    readonly_fields = ('call_history',)
    
    def get_user(self, obj):
        return obj.call_history.user
    get_user.short_description = 'User'
    
    def get_executive(self, obj):
        return obj.call_history.executive
    get_executive.short_description = 'Executive'
