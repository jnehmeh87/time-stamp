from django.urls import path
from . import views

app_name = 'workspaces'

urlpatterns = [
    # Projects
    path('projects/', views.ProjectListView.as_view(), name='project_list'),
    path('projects/new/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:pk>/update/', views.ProjectUpdateView.as_view(), name='project_update'),
    path('projects/<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
    path('projects/<int:pk>/archive/', views.project_archive, name='project_archive'),
    path('projects/bulk-archive/', views.project_bulk_archive, name='project_bulk_archive'),

    # Time Entries
    path('entries/', views.TimeEntryListView.as_view(), name='entry_list'),
    path('entries/new/', views.TimeEntryCreateView.as_view(), name='entry_create'),
    path('entries/<int:pk>/update/', views.TimeEntryUpdateView.as_view(), name='entry_update'),
    path('entries/<int:pk>/delete/', views.TimeEntryDeleteView.as_view(), name='entry_delete'),
    path('entries/bulk-delete-confirm/', views.time_entry_bulk_delete_confirm, name='time_entry_bulk_delete_confirm'),
    path('entries/bulk-delete/', views.time_entry_bulk_delete, name='time_entry_bulk_delete'),
    path('entries/bulk-archive-confirm/', views.time_entry_bulk_archive_confirm, name='time_entry_bulk_archive_confirm'),
    path('entries/bulk-unarchive-confirm/', views.time_entry_bulk_unarchive_confirm, name='time_entry_bulk_unarchive_confirm'),
    path('entries/bulk-archive/', views.time_entry_bulk_archive, name='time_entry_bulk_archive'),
    path('entries/<int:pk>/toggle-archive/', views.time_entry_toggle_archive, name='time_entry_toggle_archive'),

    # AJAX
    path('ajax/get_time_entry_details/<int:pk>/', views.get_time_entry_details, name='ajax_get_time_entry_details'),
    path('ajax/delete_time_entry_image/<int:pk>/', views.delete_time_entry_image, name='ajax_delete_time_entry_image'),
    path('ajax/get_projects_for_category/', views.get_projects_for_category, name='ajax_get_projects_for_category'),
    path('ajax/get_project_dates/', views.get_project_dates, name='ajax_get_project_dates'),
]