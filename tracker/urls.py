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

    # Time Entries
    path('entries/', views.TimeEntryListView.as_view(), name='entry_list'),
    path('entries/new/', views.TimeEntryCreateView.as_view(), name='entry_create'),
    path('entries/<int:pk>/update/', views.TimeEntryUpdateView.as_view(), name='entry_update'),
    path('entries/<int:pk>/delete/', views.TimeEntryDeleteView.as_view(), name='entry_delete'),
    path('entries/<int:pk>/archive/', views.time_entry_toggle_archive, name='entry_toggle_archive'),

    # Bulk Actions
    path('entries/bulk-delete-confirm/', views.time_entry_bulk_delete_confirm, name='entry_bulk_delete_confirm'),
    path('entries/bulk-delete/', views.time_entry_bulk_delete, name='entry_bulk_delete'),
    path('entries/bulk-archive-confirm/', views.time_entry_bulk_archive_confirm, name='entry_bulk_archive_confirm'),
    path('entries/bulk-unarchive-confirm/', views.time_entry_bulk_unarchive_confirm, name='entry_bulk_unarchive_confirm'),
    path('entries/bulk-archive/', views.time_entry_bulk_archive, name='entry_bulk_archive'),

    # Projects
    path('projects/', views.ProjectListView.as_view(), name='project_list'),
    path('projects/new/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:pk>/update/', views.ProjectUpdateView.as_view(), name='project_update'),
    path('projects/<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
    path('projects/<int:pk>/archive/', views.project_archive_confirm, name='project_archive_confirm'),
    path('projects/<int:pk>/unarchive/', views.project_unarchive_confirm, name='project_unarchive_confirm'),
    path('projects/<int:pk>/toggle-archive/', views.project_toggle_archive, name='project_toggle_archive'),

    # Reports & Analytics
    path('reports/', views.ReportView.as_view(), name='reports'),
    path('reports/translate/', views.translate_report, name='translate_report'),
    path('analytics/', views.AnalyticsDashboardView.as_view(), name='analytics'),
    path('income/', views.income_calculator, name='income_calculator'),
    path('daily-earnings/', views.daily_earnings_tracker, name='daily_earnings_tracker'),

    # AJAX
    path('ajax/get-projects/', views.get_projects_for_category, name='ajax_get_projects'),
    path('ajax/get-project-dates/', views.get_project_dates, name='ajax_get_project_dates'),
]
