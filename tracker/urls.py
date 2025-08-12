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
    path('entry/<int:pk>/delete/', views.TimeEntryDeleteView.as_view(), name='entry_delete'),
    path('reports/', views.ReportView.as_view(), name='reports'),
    path('reports/translate/', views.translate_report, name='translate_report'),
    path('projects/', views.ProjectListView.as_view(), name='project_list'),
    path('projects/ajax/add/', views.add_project_ajax, name='project_add_ajax'),
    path('projects/ajax/get-dates/', views.get_project_dates, name='project_get_dates'),
    path('projects/create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:pk>/update/', views.ProjectUpdateView.as_view(), name='project_update'),
    path('projects/<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
]
