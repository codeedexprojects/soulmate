from django.urls import path, include
from .views import *

urlpatterns = [

    path('register-executive/', RegisterExecutiveView.as_view(), name='register_executive'),
    path('login-executive/', ExecutiveLoginView.as_view(), name='login_executive'),
    path('executive/register-login/', ExeRegisterOrLoginView.as_view(), name='executive-register-login'),
    path('executive/verify-otp/', ExeVerifyOTPView.as_view(), name='executive-verify-otp'),
    path('logout-executive/<int:executive_id>/', ExecutiveLogoutView.as_view(), name='logout-executive'),

    path('executive/fixed-login/', FixedCredentialLoginView.as_view(), name='executive-fixed-login'),
    path('executive/fixed-verify-otp/', FixedCredentialVerifyOTPView.as_view(), name='executive-fixed-verify-otp'),

    path('all-executives/', ListExecutivesView.as_view(), name='list_executives'),
    path('single-executives/<int:pk>/', ExecutiveDetailView.as_view(), name='executive-detail'),
    path('executives-byuser/<int:user_id>/', ListExecutivesByUserView.as_view(), name='executives-by-user'),
    path('executive/<str:executive_id>/get-profile-picture/', ExecutiveProfileGetPictureView.as_view(), name='executive-profile-picture'),
    path('executive/profile-pictures/approval/', ExecutiveProfilePictureApprovalListView.as_view(), name='approval-list'),
    path('executive/<str:executive_id>/single-profile-picture/', ExecutiveProfilePictureSingleView.as_view(), name='executive-profile-picture'),

    path('executive/<str:executive_id>/upload/', ExecutiveProfilePictureUploadView.as_view(), name='upload-profile-picture'),
    path('executive/<str:executive_id>/approve-reject/', ExecutiveProfilePictureApprovalView.as_view(), name='approve-reject-profile-picture'),
    path('executives/<int:pk>/set_online/', SetOnlineView.as_view(), name='set_online'),
    path('executives/<int:pk>/set_offline/', SetOfflineView.as_view(), name='set_offline'),
    path('executives/<int:pk>/online/', SetOnlineStatusView.as_view(), name='set_online'),

    path('ban-executive/<str:executive_id>/', BanExecutiveAPIView.as_view(), name='ban_executive'),
    path('executive-unban/<str:executive_id>/', UnbanExecutiveView.as_view(), name='unban_executive'),

    path('executive-suspend/<int:executive_id>/', SuspendExecutiveView.as_view(), name='suspend_executive'),
    path('executive-unsuspend/<int:executive_id>/', UnsuspendExecutiveView.as_view(), name='unsuspend_executive'),
    path('executive-coin-balance/<int:executive_id>/', ExecutiveCoinBalanceView.as_view(), name='executive-coin-balance'),

    path('redeem/<int:executive_id>/<int:coin_conversion_id>/', CoinRedemptionRequestView.as_view(), name='create-redeem-request'),
    path('redeem/', CoinRedemptionRequestView.as_view(), name='list-all-redeem-requests'), 
    path('redeem/<int:executive_id>/', CoinRedemptionRequestView.as_view(), name='list-executive-redeem-requests'), 
    path('redeem-requests/', RedemptionRequestListView.as_view(), name='list_redeem_requests'),
    path('delete-executive/<int:executive_id>/', DeleteExecutiveAccountView.as_view(), name='delete-executive-account'),
    
    path('manager/executives/create/', CreateExecutiveView.as_view(), name='create-executive'),
    path('manager/executives/', ExecutiveListView.as_view(), name='list-executives'),
    path('manager/executives/<int:pk>/', ExecutiveDetailsView.as_view(), name='executive-detail'),
    path('manager/executiveslist/', ManagerExecutiveListCreateView.as_view(), name='manager-executives'),
    path('manager-executives-list/', AdminManagerExecutiveListView.as_view(), name='manager-executives'),

]
