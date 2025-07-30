from django.urls import path
from .views import *

urlpatterns = [


    path('register-or-login/', RegisterOrLoginView.as_view(), name='register_or_login'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('delete-user/<int:user_id>/', DeleteUserAccountView.as_view(), name='delete-user-account'),

    
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/<int:id>/', UserDetailView.as_view(), name='user_detail'),
    path('user/<int:user_id>/coin-balance/', GetUserCoinBalanceView.as_view(), name='get_user_coin_balance'),
    path('update-dp/', UpdateDPImageView.as_view(), name='update-dp'),

    path('add-favourite/<int:user_id>/<int:executive_id>/', add_favourite, name='add_favourite'),
    path('list-favourites/<int:user_id>/', ListFavouritesView.as_view(), name='list_favourites'),
    path('remove-favourite/<int:user_id>/<int:executive_id>/', RemoveFavouriteView.as_view(), name='remove_favourite'),
    path('ratings/<int:executive_id>/', get_ratings, name='get_ratings'),
    path('average-rating/<int:executive_id>/', average_rating, name='average_rating'),
    path('average-ratings/', average_rating_all_executives, name='average_rating_all_executives'),
    path('user/<int:user_id>/executive-ratings/', UserExecutiveRatingsView.as_view(), name='user-executive-ratings'),
    path('user-Total-ratings/', UserExecutiveTotalRatingsView.as_view(), name='user-Total-ratings'),

    path('rate/<int:user_id>/<int:executive_id>/', RateExecutiveView.as_view(), name='create_rating'),

    path('mycoins/<int:user_id>/', UserCoinBalanceView.as_view(), name='user_coin_balance'),
    path('carousel-images/', CarouselImageListCreateView.as_view(), name='carousel_image_list_create'),
    path('carousel-images/<int:image_id>/', CarouselImageDetailView.as_view(), name='carousel_image_detail'),
    path('careers/', CareerListCreateView.as_view(), name='career_list_create'),
    path('careers/<int:id>/', CareerDetailView.as_view(), name='career_detail'),


    path('ban-user/<int:user_id>/', BanUserAPIView.as_view(), name='ban_user'),
    path('user-unban/<int:user_id>/', UnbanUserView.as_view(), name='unban_user'),
    path('users/banned/', BannedUserListView.as_view(), name='banned-users'),

    path('user-suspend/<int:user_id>/', SuspendUserView.as_view(), name='suspend_user'),
    path('user-unsuspend/<int:user_id>/', UnsuspendUserView.as_view(), name='unsuspend_user'),
    path('block-user/', BlockUserAPIView.as_view(), name='block_user'),
    
    path('unblock-user/', UnblockUserAPIView.as_view(), name='unblock_user'),
    path('blocked-users/<int:executive_id>/', BlockedUsersListAPIView.as_view(), name='blocked-users-list'),
    path('blocked-users/list/', Blocked_UserListAPIView.as_view(), name='blocked-users-list-admin'),

    path('referral-code/<int:user_id>/', ReferralCodeByUserView.as_view(), name='referral-code-by-user'),
    
    path('user/referral/<int:user_id>/', ReferralDetailsView.as_view(), name='user-referral-details'),
    path('referral-history/', ReferralHistoryListView.as_view(), name='referral-history-list'),

]



