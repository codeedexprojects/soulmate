from django.urls import path
from .views import *

urlpatterns = [

    path('full_report/', PlatformAnalyticsView.as_view(), name='platform_analysis'),
    path('log-call/<int:user_id>/', LogCallView.as_view(), name='log_call'),
    path('call-statistics/daily/', DailyCallStatisticsView.as_view(), name='daily-call-statistics'),
    path('call-statistics/weekly/', WeeklyCallStatisticsView.as_view(), name='weekly-call-statistics'),
    path('call-statistics/monthly/', MonthlyCallStatisticsView.as_view(), name='monthly-call-statistics'),

    path('executive/<int:executive_id>/status/', ExecutiveStatusView.as_view(), name='executive_status'),

    path('exe-call-history/<int:executive_id>/', TalkTimeHistoryByExecutiveView.as_view(), name='call-history'),
    path('exe-call-history/<int:executive_id>/user/<int:user_id>/', TalkTimeHistoryByExecutiveAndUserView.as_view(), name='call-history-by-executive-and-user'),

    path('create-admin/', CreateAdminView.as_view(), name='create-admin'),
    path('admin-login/', SuperuserLoginView.as_view(), name='admin-login'),
    path('admin/update/<int:pk>/',AdminDetailUpdate.as_view(), name='update-admin'),
    path('password-reset/send-otp/', SendPasswordResetOTPView.as_view(), name='send-password-reset-otp'),
    path('password-reset/verify-otp/', VerifyOTPResetPasswordView.as_view(), name='verify-password-reset-otp'),
    path('admin-logout/', AdminLogoutView.as_view(), name='admin_logout'),
    path('admins/', ListAdminView.as_view(), name='list-admins'),
    path('executives/under-manager/<int:manager_id>/', ExecutivesUnderManagerView.as_view(), name="executives-under-manager"),

    path('up-del-revenue-target/<int:pk>/', RevenueTargetView.as_view(), name='revenue-target'),

    path('get-target/', RevenueCreateTargetView.as_view(), name='revenue_target'),
    path('executive-statistics/<int:executive_id>/', ExecutiveStatisticsAPIView.as_view(), name='executive-statistics'),

    path('executive-stats/', ExecutiveStatsAPIView.as_view(), name='executive-stats'),
    path('ongoing-calls/', OngoingCallsAPIView.as_view(), name='ongoing-calls'),
    path('user/<int:user_id>/call-duration/', UserCallDurationView.as_view(), name='user-call-duration'),

    path('executives/stats/<int:pk>/', ExecutiveStatsView.as_view({'get': 'retrieve'}), name='executive-stats-detail'),

    path('executives/<int:executive_id>/ratings/', ExecutiveCallRatingListView.as_view(), name='executive-call-ratings'),
    path('ratings/', CallRatingListView.as_view(), name='all-call-ratings'),
    path('ratings/create/<int:user_id>/<int:execallhistory_id>/', CallRatingCreateView.as_view(), name='create-call-rating'),
    path('ratings/<int:rating_id>/', CallRatingDetailView.as_view(), name='call-rating-detail'),

    path('executives/<int:executive_id>/update-on-call/', UpdateExecutiveOnCallStatus.as_view(), name='update-on-call'),
    path('total-coins-spend/<str:user_id>/', TotalCoinsDeductedView.as_view(), name='total-coins-deducted'),
    path('executive-report/<int:executive_id>/', ExecutiveAnalyticsView.as_view(), name='executive-analytics'),

]




    