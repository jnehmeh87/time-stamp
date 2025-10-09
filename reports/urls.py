from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.ReportView.as_view(), name='reports'),
    path('translate/', views.TranslateReportView.as_view(), name='translate_report'),
]