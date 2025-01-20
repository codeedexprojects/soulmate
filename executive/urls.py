from django.urls import path, include
from .views import *

urlpatterns = [

    path('register-executive/', RegisterExecutiveView.as_view(), name='register_executive'),
    path('login-executive/', ExecutiveLoginView.as_view(), name='login_executive'),
    path('executive/register-login/', ExeRegisterOrLoginView.as_view(), name='executive-register-login'),
    path('executive/verify-otp/', ExeVerifyOTPView.as_view(), name='executive-verify-otp'),

    path('all-executives/', ListExecutivesView.as_view(), name='list_executives'),
    path('single-executives/<int:pk>/', ExecutiveDetailView.as_view(), name='executive-detail'),
    path('executives-byuser/<int:user_id>/', ListExecutivesByUserView.as_view(), name='executives-by-user'),
    path('executive/<str:executive_id>/get-profile-picture/', ExecutiveProfileGetPictureView.as_view(), name='executive-profile-picture'),

    path('executive/<str:executive_id>/upload/', ExecutiveProfilePictureUploadView.as_view(), name='upload-profile-picture'),
    path('executive/<str:executive_id>/approve-reject/', ExecutiveProfilePictureApprovalView.as_view(), name='approve-reject-profile-picture'),
    path('executives/<int:pk>/set_online/', SetOnlineView.as_view(), name='set_online'),
    path('executives/<int:pk>/set_offline/', SetOfflineView.as_view(), name='set_offline'),
    path('executives/<int:pk>/online/', SetOnlineStatusView.as_view(), name='set_online'),

    path('executive/<int:executive_id>/status/', ExecutiveStatusView.as_view(), name='executive_status'),

    path('exe-call-history/<int:executive_id>/', TalkTimeHistoryByExecutiveView.as_view(), name='call-history'),
    path('exe-call-history/<int:executive_id>/user/<int:user_id>/', TalkTimeHistoryByExecutiveAndUserView.as_view(), name='call-history-by-executive-and-user'),

    path('create-admin/', CreateAdminView.as_view(), name='create-admin'),
    path('admin-login/', SuperuserLoginView.as_view(), name='admin-login'),
    path('admin-logout/', AdminLogoutView.as_view(), name='admin_logout'),
    path('admins/', ListAdminView.as_view(), name='list-admins'),


    path('ban-executive/<str:executive_id>/', BanExecutiveAPIView.as_view(), name='ban_executive'),
    path('executive-unban/<str:executive_id>/', UnbanExecutiveView.as_view(), name='unban_executive'),

    path('executive-suspend/<int:executive_id>/', SuspendExecutiveView.as_view(), name='suspend_executive'),
    path('executive-unsuspend/<int:executive_id>/', UnsuspendExecutiveView.as_view(), name='unsuspend_executive'),
    path('call-history/', CallHistoryViewSet.as_view({'get': 'list'}), name='callhistory-list'),
    path('call-history/<int:pk>/', CallHistoryViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}), name='callhistory-detail'),
    path('executive-coin-balance/<int:executive_id>/', ExecutiveCoinBalanceView.as_view(), name='executive-coin-balance'),

    path('redeem/<int:executive_id>/<int:coin_conversion_id>/', CoinRedemptionRequestView.as_view(), name='create-redeem-request'),
    path('redeem/', CoinRedemptionRequestView.as_view(), name='list-all-redeem-requests'), 
    path('redeem/<int:executive_id>/', CoinRedemptionRequestView.as_view(), name='list-executive-redeem-requests'), 
    path('redeem-requests/', RedemptionRequestListView.as_view(), name='list_redeem_requests'),

    path('up-del-revenue-target/<int:pk>/', RevenueTargetView.as_view(), name='revenue-target'),

    path('get-target/', RevenueCreateTargetView.as_view(), name='revenue_target'),
    path('executive-statistics/<int:executive_id>/', ExecutiveStatisticsAPIView.as_view(), name='executive-statistics'),

    path('executive-stats/', ExecutiveStatsAPIView.as_view(), name='executive-stats'),
    path('ongoing-calls/', OngoingCallsAPIView.as_view(), name='ongoing-calls'),
    path('user/<int:user_id>/call-duration/', UserCallDurationView.as_view(), name='user-call-duration'),

    path('executives/stats/<int:pk>/', ExecutiveStatsView.as_view({'get': 'retrieve'}), name='executive-stats-detail'),
    path('coin-conversions/', CoinConversionListCreateView.as_view(), name='coin-conversion-list-create'),

    path('executives/<int:executive_id>/ratings/', ExecutiveCallRatingListView.as_view(), name='executive-call-ratings'),
    path('ratings/', CallRatingListView.as_view(), name='all-call-ratings'),
    path('ratings/create/<int:user_id>/<int:execallhistory_id>/', CallRatingCreateView.as_view(), name='create-call-rating'),
    path('ratings/<int:rating_id>/', CallRatingDetailView.as_view(), name='call-rating-detail'),

    path('executives/<int:executive_id>/update-on-call/', UpdateExecutiveOnCallStatus.as_view(), name='update-on-call'),
    path('total-coins-spend/<str:user_id>/', TotalCoinsDeductedView.as_view(), name='total-coins-deducted'),
    path('delete-executive/<int:executive_id>/', DeleteExecutiveAccountView.as_view(), name='delete-executive-account'),
    
]
