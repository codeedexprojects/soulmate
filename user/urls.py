from django.urls import path
from .views import *

urlpatterns = [


    path('register-or-login/', RegisterOrLoginView.as_view(), name='register_or_login'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('delete-user/<int:user_id>/', DeleteUserAccountView.as_view(), name='delete-user-account'),

    
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/<int:id>/', UserDetailView.as_view(), name='user_detail'),
    path('user/<int:user_id>/coin-balance/', GetUserCoinBalanceView.as_view(), name='get_user_coin_balance'),
    path('add-favourite/<int:user_id>/<int:executive_id>/', add_favourite, name='add_favourite'),
    path('list-favourites/<int:user_id>/', ListFavouritesView.as_view(), name='list_favourites'),
    path('remove-favourite/<int:user_id>/<int:executive_id>/', RemoveFavouriteView.as_view(), name='remove_favourite'),
    path('ratings/<int:executive_id>/', get_ratings, name='get_ratings'),
    path('average-rating/<int:executive_id>/', average_rating, name='average_rating'),
    path('average-ratings/', average_rating_all_executives, name='average_rating_all_executives'),
    path('user/<int:user_id>/executive-ratings/', UserExecutiveRatingsView.as_view(), name='user-executive-ratings'),
    path('user-Total-ratings/', UserExecutiveTotalRatingsView.as_view(), name='user-Total-ratings'),


    # path('calls/end/<int:call_history_id>/', EndCallByHistoryView.as_view(), name='end-call-by-history'),

    path('call-history/<int:user_id>/', call_history, name='call_history'),
    path('rate/<int:user_id>/<int:executive_id>/', RateExecutiveView.as_view(), name='create_rating'),
    path('log-call/<int:user_id>/', LogCallView.as_view(), name='log_call'),
    path('recharge-plan-categories/', RechargePlanCategoryListCreateView.as_view(), name='recharge-plan-category-list-create'),
    path('recharge-plan-categories/<int:pk>/', RechargePlanCategoryDetailView.as_view(), name='recharge-plan-category-detail'),
    path('recharge/<int:user_id>/', RechargeCoinsView.as_view(), name='recharge-coins'),
    path('recharge-plan-create/', CreateRechargePlanView.as_view(), name='create_recharge_plan'),
    path('recharge-plans/', ListRechargePlansView.as_view(), name='list_recharge_plans'),
    path('recharge-plans/<int:id>/', RechargePlanDetailView.as_view(), name='recharge-plan-detail'),
    path('recharge/<int:user_id>/plan/<int:plan_id>/', CreateRazorpayOrderView.as_view(), name='create-razorpay-order'),
    path('payment/success/<str:razorpay_order_id>/', HandlePaymentSuccessView.as_view(), name='handle-payment-success'),
    path('recharge-admin/<int:user_id>/plan/<int:plan_id>/', RechargeCoinsByPlanView.as_view(), name='recharge-by-plan'),
    path('categories-with-plans/', CategoryWithPlansListView.as_view(), name='categories-with-plans'),
    path('categories-with-plans/<int:category_id>/', RechargePlanListByCategoryView.as_view(), name='categories-with-plans-id'),


    path('mycoins/<int:user_id>/', UserCoinBalanceView.as_view(), name='user_coin_balance'),
    path('carousel-images/', CarouselImageListCreateView.as_view(), name='carousel_image_list_create'),
    path('carousel-images/<int:image_id>/', CarouselImageDetailView.as_view(), name='carousel_image_detail'),
    path('careers/', CareerListCreateView.as_view(), name='career_list_create'),
    path('careers/<int:id>/', CareerDetailView.as_view(), name='career_detail'),
    path('purchase-history/<int:user_id>/', UserPurchaseHistoryView.as_view(), name='purchase-history'),
    path('statistics/', StatisticsAPIView.as_view(), name='statistics'),
    path('user-statistics/', UserStatisticsAPIView.as_view(), name='user-statistics'),
    path('user-statistics/<int:user_id>/', UserStatisticsDetailAPIView.as_view(), name='user-statistics'),  # Use user_id in URL
    path('call-statistics/daily/', DailyCallStatisticsView.as_view(), name='daily-call-statistics'),
    path('call-statistics/weekly/', WeeklyCallStatisticsView.as_view(), name='weekly-call-statistics'),
    path('call-statistics/monthly/', MonthlyCallStatisticsView.as_view(), name='monthly-call-statistics'),

    path('ban-user/<int:user_id>/', BanUserAPIView.as_view(), name='ban_user'),
    path('user-unban/<int:user_id>/', UnbanUserView.as_view(), name='unban_user'),

    path('user-suspend/<int:user_id>/', SuspendUserView.as_view(), name='suspend_user'),
    path('user-unsuspend/<int:user_id>/', UnsuspendUserView.as_view(), name='unsuspend_user'),

    path('referral-code/<int:user_id>/', ReferralCodeByUserView.as_view(), name='referral-code-by-user'),
    path('join-channel/', JoinChannelView.as_view(), name='join-channel'),
    path('leave-channel/', LeaveChannelView.as_view(), name='leave-channel'),


    path('create_channel/', CreateChannelView.as_view(), name='create_channel'),

    # Executive views the created channel
    path('receive-channel/<int:executive_id>/', GetRecentChannelView.as_view(), name='get-recent-channel'),

    path('view_channel_for_executive/', ViewChannelForExecutiveView.as_view(), name='view_channel_for_executive'),

    # Executive joins the channel
    path('join_channel_for_executive/', JoinChannelForExecutiveView.as_view(), name='join_channel_for_executive'),

    # Check channel status (connected or missed)
    path('callstatus/<int:call_id>/', GetCallStatusView.as_view(), name='channel_status'),

    # Executive leaves the channel
    path('leave_channel_for_executive/', LeaveChannelForExecutiveView.as_view(), name='leave_channel_for_executive'),
    path('leave_channel_for_user/', LeaveChannelForUserView.as_view(), name='leave_channel_for_user'),
    path('leave-all-calls/', LeaveAllCallsForExecutiveView.as_view(), name='leave_all_calls_for_executive'),


]



