from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    # Home & Timer
    path('', views.HomePageView.as_view(), name='home'),
    path('start/', views.start_timer, name='start_timer'),
    path('stop/', views.stop_timer, name='stop_timer'),

    # Time Entries
    path('entries/', views.TimeEntryListView.as_view(), name='entry_list'),
    path('entry/create/', views.TimeEntryCreateView.as_view(), name='entry_create'),
    path('entry/<int:pk>/update/', views.TimeEntryUpdateView.as_view(), name='entry_update'),
    path('entry/<int:pk>/delete/', views.TimeEntryDeleteView.as_view(), name='entry_delete'),
    path('entry/<int:pk>/toggle-archive/', views.time_entry_toggle_archive, name='entry_toggle_archive'),

    # Bulk Actions
    path('entries/bulk-delete/confirm/', views.time_entry_bulk_delete_confirm, name='entry_bulk_delete_confirm'),
    path('entries/bulk-delete/', views.time_entry_bulk_delete, name='entry_bulk_delete'),
    path('entries/bulk-archive/confirm/', views.time_entry_bulk_archive_confirm, name='entry_bulk_archive_confirm'),
    path('entries/bulk-unarchive/confirm/', views.time_entry_bulk_unarchive_confirm, name='entry_bulk_unarchive_confirm'),
    path('entries/bulk-archive/', views.time_entry_bulk_archive, name='entry_bulk_archive'),

    # Projects
    path('projects/', views.ProjectListView.as_view(), name='project_list'),
    path('project/create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('project/<int:pk>/update/', views.ProjectUpdateView.as_view(), name='project_update'),
    path('project/<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),

    # Reports & Translation
    path('reports/', views.ReportView.as_view(), name='reports'),
    path('reports/translate/', views.translate_report, name='translate_report'),

    # AJAX
    path('ajax/get-project-dates/', views.get_project_dates, name='project_get_dates'),
]
