from django.urls import path
from .views import *

urlpatterns = [
    path('recharge-plan-categories/', RechargePlanCategoryListCreateView.as_view(), name='recharge-plan-category-list-create'),
    path('recharge-plan-categories/<int:pk>/', RechargePlanCategoryDetailView.as_view(), name='recharge-plan-category-detail'),
    path('recharge/<int:user_id>/', RechargeCoinsView.as_view(), name='recharge-coins'),
    path('recharge-plan-create/', CreateRechargePlanView.as_view(), name='create_recharge_plan'),
    path('recharge-plans/', ListRechargePlansView.as_view(), name='list_recharge_plans'),
    path('recharge-plans/<int:id>/', RechargePlanDetailView.as_view(), name='recharge-plan-detail'),
    path('recharge/<int:user_id>/plan/<int:plan_id>/', CreateRazorpayOrderView.as_view(), name='create-razorpay-order'),
    path('razorpay/latest-order/<int:user_id>/', GetLatestRazorpayOrderView.as_view(), name='latest-razorpay-order'),

    path('razorpay/verify-payment/<str:order_id>/', VerifyPaymentView.as_view()),

    path('payment/success/<str:razorpay_order_id>/', HandlePaymentSuccessView.as_view(), name='handle-payment-success'),
    path('recharge-admin/<int:user_id>/plan/<int:plan_id>/', RechargeCoinsByPlanView.as_view(), name='recharge-by-plan'),
    path('categories-with-plans/', CategoryWithPlansListView.as_view(), name='categories-with-plans'),
    path('categories-with-plans/<int:category_id>/', RechargePlanListByCategoryView.as_view(), name='categories-with-plans-id'),
    path('purchase-history/<int:user_id>/', UserPurchaseHistoriesView.as_view(), name='purchase-history'),
    path('user/purchase-history/', PurchaseHistoryListView.as_view(), name='purchase-history'),
    path('statistics/', StatisticsAPIView.as_view(), name='statistics'),
    path('user-statistics/', UserStatisticsAPIView.as_view(), name='user-statistics'),
    path('user-statistics/<int:user_id>/', UserStatisticsDetailAPIView.as_view(), name='user-statistics'),
    path('coin-conversions/', CoinConversionListCreateView.as_view(), name='coin-conversion-list-create'),
    path('coin-conversion/<int:pk>/', CoinConversionUpdateView.as_view(), name='coin-conversion-update'),
    path('cashfree/<int:user_id>/<int:plan_id>/', CreatePaymentLinkView.as_view(), name='create-payment-link'),
    path('get-payment-details/<int:user_id>/', GetPaymentDetailsView.as_view(), name='get-payment-details'),
    path('purchase-by-admin/', PurchaseDoneByAdminHistoryView.as_view(), name='admin-purchase-history'),

    path('cashfree/webhook/<str:order_id>/', cashfree_webhook, name='cashfree-webhook'),

    
    ]













