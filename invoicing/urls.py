from django.urls import path
from . import views

app_name = 'invoicing'

urlpatterns = [
    path('', views.InvoiceListView.as_view(), name='invoice_list'),
]
