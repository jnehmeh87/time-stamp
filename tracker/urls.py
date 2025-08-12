from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    path('', views.HomePageView.as_view(), name='home'),
    path('start/', views.start_timer, name='start_timer'),
    path('stop/', views.stop_timer, name='stop_timer'),
    path('entries/', views.TimeEntryListView.as_view(), name='entry_list'),
    path('entry/<int:pk>/update/', views.TimeEntryUpdateView.as_view(), name='entry_update'),
    path('entry/<int:pk>/toggle-archive/', views.toggle_entry_archive, name='entry_toggle_archive'),
    path('reports/', views.ReportView.as_view(), name='reports'),
    path('projects/', views.ProjectListView.as_view(), name='project_list'),
    path('projects/create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:pk>/update/', views.ProjectUpdateView.as_view(), name='project_update'),
    path('projects/<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
]
