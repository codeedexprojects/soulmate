from django.urls import path
from .views import *

urlpatterns = [

    
    path('call-history/', CallHistoryViewSet.as_view({'get': 'list'}), name='callhistory-list'),
    path('call-history/<int:pk>/', CallHistoryViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}), name='callhistory-detail'),

    path('ongoing-calls/', OngoingCallsAPIView.as_view(), name='ongoing-calls'),

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



