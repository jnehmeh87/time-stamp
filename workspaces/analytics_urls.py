from django.urls import path
from . import analytics_views as views

app_name = 'analytics'

urlpatterns = [
    path('', views.AnalyticsDashboardView.as_view(), name='dashboard'),
    path('daily-earnings/', views.DailyEarningsTrackerView.as_view(), name='daily_earnings_tracker'),
    path('income-calculator/', views.IncomeCalculatorView.as_view(), name='income_calculator'),
]
