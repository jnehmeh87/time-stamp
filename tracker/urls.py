from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    # Home & Timer
    path('', views.HomePageView.as_view(), name='home'),
    path('timer/start/', views.start_timer, name='start_timer'),
    path('timer/stop/', views.stop_timer, name='stop_timer'),
    path('timer/pause/', views.pause_timer, name='pause_timer'),
    path('timer/resume/', views.resume_timer, name='resume_timer'),

    # AJAX URLs
    path('ajax/session-keep-alive/', views.session_keep_alive, name='session_keep_alive'),

    # Reports & Analytics
    path('reports/', views.ReportView.as_view(), name='reports'),
    path('reports/translate/', views.translate_report, name='translate_report'),
    path('analytics/', views.AnalyticsDashboardView.as_view(), name='analytics'),
    path('income/', views.income_calculator, name='income_calculator'),
    path('daily-earnings/', views.daily_earnings_tracker, name='daily_earnings_tracker'),

    # Profile
]
