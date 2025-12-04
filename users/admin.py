# from django.contrib import admin
# from .models import User, UserProfile, Favourite, Rating, CarouselImage, Career, ReferralCode, ReferralHistory, UserBlock, DeletedUser


# @admin.register(User)
# class UserAdmin(admin.ModelAdmin):
#     list_display = ('user_id', 'name', 'email', 'mobile_number', 'gender', 'coin_balance', 'is_verified', 'is_banned', 'is_suspended', 'is_dormant', 'is_online', 'created_at')
#     list_filter = ('gender', 'is_verified', 'is_banned', 'is_suspended', 'is_dormant', 'is_online', 'is_deleted', 'is_active', 'created_at')
#     search_fields = ('user_id', 'name', 'email', 'mobile_number')
#     readonly_fields = ('user_id', 'created_at', 'last_login')
#     ordering = ('-created_at',)
    
#     fieldsets = (
#         ('Personal Information', {
#             'fields': ('user_id', 'name', 'email', 'mobile_number', 'gender')
#         }),
#         ('Profile', {
#             'fields': ('dp_image',)
#         }),
#         ('Account Status', {
#             'fields': ('is_verified', 'is_active', 'is_banned', 'is_suspended', 'is_dormant', 'is_deleted', 'is_online')
#         }),
#         ('Coins', {
#             'fields': ('coin_balance',)
#         }),
#         ('Permissions', {
#             'fields': ('is_staff', 'groups', 'user_permissions')
#         }),
#         ('Authentication', {
#             'fields': ('otp',),
#             'classes': ('collapse',)
#         }),
#         ('Timestamps', {
#             'fields': ('created_at', 'last_login'),
#             'classes': ('collapse',)
#         }),
#     )
    
#     actions = ['ban_users', 'unban_users', 'suspend_users', 'unsuspend_users', 'verify_users', 'mark_as_dormant', 'mark_as_active', 'set_online', 'set_offline']
    
#     def ban_users(self, request, queryset):
#         updated = queryset.update(is_banned=True)
#         self.message_user(request, f'{updated} user(s) banned.')
#     ban_users.short_description = "Ban selected users"
    
#     def unban_users(self, request, queryset):
#         updated = queryset.update(is_banned=False)
#         self.message_user(request, f'{updated} user(s) unbanned.')
#     unban_users.short_description = "Unban selected users"
    
#     def suspend_users(self, request, queryset):
#         updated = queryset.update(is_suspended=True)
#         self.message_user(request, f'{updated} user(s) suspended.')
#     suspend_users.short_description = "Suspend selected users"
    
#     def unsuspend_users(self, request, queryset):
#         updated = queryset.update(is_suspended=False)
#         self.message_user(request, f'{updated} user(s) unsuspended.')
#     unsuspend_users.short_description = "Unsuspend selected users"
    
#     def verify_users(self, request, queryset):
#         updated = queryset.update(is_verified=True)
#         self.message_user(request, f'{updated} user(s) verified.')
#     verify_users.short_description = "Verify selected users"
    
#     def mark_as_dormant(self, request, queryset):
#         updated = queryset.update(is_dormant=True)
#         self.message_user(request, f'{updated} user(s) marked as dormant.')
#     mark_as_dormant.short_description = "Mark selected users as dormant"
    
#     def mark_as_active(self, request, queryset):
#         updated = queryset.update(is_dormant=False)
#         self.message_user(request, f'{updated} user(s) marked as active.')
#     mark_as_active.short_description = "Mark selected users as active"
    
#     def set_online(self, request, queryset):
#         updated = queryset.update(is_online=True)
#         self.message_user(request, f'{updated} user(s) set to online.')
#     set_online.short_description = "Set selected users as online"
    
#     def set_offline(self, request, queryset):
#         updated = queryset.update(is_online=False)
#         self.message_user(request, f'{updated} user(s) set to offline.')
#     set_offline.short_description = "Set selected users as offline"


# @admin.register(UserProfile)
# class UserProfileAdmin(admin.ModelAdmin):
#     list_display = ('user', 'coin_balance')
#     search_fields = ('user__name', 'user__email', 'user__mobile_number')
#     readonly_fields = ('user',)
    
#     fieldsets = (
#         ('User Profile', {
#             'fields': ('user', 'coin_balance')
#         }),
#     )


# @admin.register(Favourite)
# class FavouriteAdmin(admin.ModelAdmin):
#     list_display = ('user', 'executive', 'created_at')
#     list_filter = ('created_at',)
#     search_fields = ('user__name', 'executive__name', 'user__mobile_number', 'executive__mobile_number')
#     readonly_fields = ('created_at',)
#     ordering = ('-created_at',)


# @admin.register(Rating)
# class RatingAdmin(admin.ModelAdmin):
#     list_display = ('user', 'executive', 'rating', 'created_at')
#     list_filter = ('rating', 'created_at')
#     search_fields = ('user__name', 'executive__name', 'user__mobile_number', 'executive__mobile_number')
#     readonly_fields = ('created_at',)
#     ordering = ('-created_at',)
    
#     fieldsets = (
#         ('Rating Details', {
#             'fields': ('user', 'executive', 'rating', 'comment')
#         }),
#         ('Timestamps', {
#             'fields': ('created_at',),
#             'classes': ('collapse',)
#         }),
#     )


# @admin.register(CarouselImage)
# class CarouselImageAdmin(admin.ModelAdmin):
#     list_display = ('title', 'created_at')
#     list_filter = ('created_at',)
#     search_fields = ('title',)
#     readonly_fields = ('created_at',)
#     ordering = ('-created_at',)
    
#     fieldsets = (
#         ('Carousel Image', {
#             'fields': ('title', 'image')
#         }),
#         ('Timestamps', {
#             'fields': ('created_at',),
#             'classes': ('collapse',)
#         }),
#     )


# @admin.register(Career)
# class CareerAdmin(admin.ModelAdmin):
#     list_display = ('full_name', 'email', 'phone_number', 'age', 'place', 'gender', 'marital_status', 'created_at')
#     list_filter = ('gender', 'marital_status', 'created_at')
#     search_fields = ('full_name', 'email', 'phone_number', 'place', 'profession')
#     readonly_fields = ('created_at',)
#     ordering = ('-created_at',)
    
#     fieldsets = (
#         ('Personal Information', {
#             'fields': ('full_name', 'email', 'phone_number', 'age', 'gender', 'marital_status', 'place')
#         }),
#         ('Professional Information', {
#             'fields': ('education', 'profession', 'spoken_languages')
#         }),
#         ('Timestamps', {
#             'fields': ('created_at',),
#             'classes': ('collapse',)
#         }),
#     )


# @admin.register(ReferralCode)
# class ReferralCodeAdmin(admin.ModelAdmin):
#     list_display = ('user', 'code')
#     search_fields = ('user__name', 'code', 'user__email')
#     readonly_fields = ('user', 'code')


# @admin.register(ReferralHistory)
# class ReferralHistoryAdmin(admin.ModelAdmin):
#     list_display = ('referrer', 'referred_user', 'recharged')
#     list_filter = ('recharged',)
#     search_fields = ('referrer__name', 'referred_user__name', 'referrer__email', 'referred_user__email')
#     readonly_fields = ('referrer', 'referred_user')
    
#     actions = ['mark_as_recharged', 'mark_as_not_recharged']
    
#     def mark_as_recharged(self, request, queryset):
#         updated = queryset.update(recharged=True)
#         self.message_user(request, f'{updated} referral(s) marked as recharged.')
#     mark_as_recharged.short_description = "Mark as Recharged"
    
#     def mark_as_not_recharged(self, request, queryset):
#         updated = queryset.update(recharged=False)
#         self.message_user(request, f'{updated} referral(s) marked as not recharged.')
#     mark_as_not_recharged.short_description = "Mark as Not Recharged"


# @admin.register(UserBlock)
# class UserBlockAdmin(admin.ModelAdmin):
#     list_display = ('user', 'executive', 'is_blocked', 'blocked_at')
#     list_filter = ('is_blocked', 'blocked_at')
#     search_fields = ('user__name', 'executive__name', 'user__mobile_number', 'executive__mobile_number')
#     readonly_fields = ('blocked_at',)
#     ordering = ('-blocked_at',)
    
#     fieldsets = (
#         ('Block Information', {
#             'fields': ('user', 'executive', 'is_blocked', 'reason')
#         }),
#         ('Timestamps', {
#             'fields': ('blocked_at',),
#             'classes': ('collapse',)
#         }),
#     )
    
#     actions = ['block_users', 'unblock_users']
    
#     def block_users(self, request, queryset):
#         updated = queryset.update(is_blocked=True)
#         self.message_user(request, f'{updated} block(s) activated.')
#     block_users.short_description = "Activate selected blocks"
    
#     def unblock_users(self, request, queryset):
#         updated = queryset.update(is_blocked=False)
#         self.message_user(request, f'{updated} block(s) deactivated.')
#     unblock_users.short_description = "Deactivate selected blocks"


# @admin.register(DeletedUser)
# class DeletedUserAdmin(admin.ModelAdmin):
#     list_display = ('mobile_number', 'deleted_at')
#     list_filter = ('deleted_at',)
#     search_fields = ('mobile_number',)
#     readonly_fields = ('deleted_at',)
#     ordering = ('-deleted_at',)
