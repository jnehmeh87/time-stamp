from django.urls import path, include
from . import views

app_name = 'workspaces'

urlpatterns = [
    # Home & Timer
    path('', views.HomePageView.as_view(), name='home'),
    path('timer/start/', views.start_timer, name='start_timer'),
    path('timer/stop/', views.stop_timer, name='stop_timer'),
    path('timer/pause/', views.pause_timer, name='pause_timer'),
    path('timer/resume/', views.resume_timer, name='resume_timer'),

    # AJAX URLs
    path('ajax/session-keep-alive/', views.session_keep_alive, name='session_keep_alive'),
    path('ajax/get-time-entry-details/<int:pk>/', views.get_time_entry_details, name='get_time_entry_details'),
    path('ajax/delete-time-entry-image/<int:pk>/', views.delete_time_entry_image, name='delete_time_entry_image'),
    path('ajax/get-projects-for-category/', views.get_projects_for_category, name='get_projects_for_category'),

    # Project URLs
    path('projects/', views.ProjectListView.as_view(), name='project_list'),
    path('projects/create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:pk>/update/', views.ProjectUpdateView.as_view(), name='project_update'),
    path('projects/<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
    path('projects/<int:pk>/archive/', views.project_toggle_archive, name='project_toggle_archive'),


    # Time Entry URLs
    path('time-entries/', views.TimeEntryListView.as_view(), name='time_entry_list'),
    path('time-entries/create/', views.TimeEntryCreateView.as_view(), name='time_entry_create'),
    path('time-entries/<int:pk>/update/', views.TimeEntryUpdateView.as_view(), name='time_entry_update'),
    path('time-entries/<int:pk>/delete/', views.TimeEntryDeleteView.as_view(), name='time_entry_delete'),
    path('time-entries/bulk-delete-confirm/', views.time_entry_bulk_delete_confirm, name='time_entry_bulk_delete_confirm'),
    path('time-entries/bulk-delete/', views.time_entry_bulk_delete, name='time_entry_bulk_delete'),
    path('time-entries/bulk-archive-confirm/', views.time_entry_bulk_archive_confirm, name='time_entry_bulk_archive_confirm'),
    path('time-entries/bulk-unarchive-confirm/', views.time_entry_bulk_unarchive_confirm, name='time_entry_bulk_unarchive_confirm'),
    path('time-entries/bulk-archive/', views.time_entry_bulk_archive, name='time_entry_bulk_archive'),
    path('time-entries/<int:pk>/toggle-archive/', views.time_entry_toggle_archive, name='time_entry_toggle_archive'),
    
    # Analytics
    path('analytics/', include('workspaces.analytics_urls', namespace='analytics')),
    
    # Contacts
    path('contacts/', views.ManageContactsView.as_view(), name='manage_contacts'),
]
