from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import api_views

router = DefaultRouter()
router.register(r'accounts', api_views.AccountViewSet, basename='account')
router.register(r'categories', api_views.CategoryViewSet, basename='category')
router.register(r'transactions', api_views.TransactionViewSet, basename='transaction')
router.register(r'budgets', api_views.BudgetViewSet, basename='budget')
router.register(r'liabilities', api_views.LiabilityViewSet, basename='liability')
router.register(r'goals', api_views.SavingsGoalViewSet, basename='goal')
router.register(r'recurring', api_views.RecurringRuleViewSet, basename='recurring')

urlpatterns = [
    path('', include(router.urls)),
    # Auth
    path('auth/register/', api_views.RegisterView.as_view(), name='api-register'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token-obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    # Dashboard
    path('dashboard/', api_views.DashboardView.as_view(), name='api-dashboard'),
    # AI
    path('ai/insights/', api_views.AIInsightsView.as_view(), name='ai-insights'),
    path('ai/nlp-transaction/', api_views.NLPTransactionView.as_view(), name='nlp-transaction'),
    path('ai/predictions/', api_views.PredictionsView.as_view(), name='predictions'),
    # Reports
    path('reports/summary/', api_views.ReportSummaryView.as_view(), name='report-summary'),
]
