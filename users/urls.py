from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('send-invitation/', views.send_invitation, name='send_invitation'),
    path('accept-invitation/<str:token>/', views.accept_invitation, name='accept_invitation'),
]
