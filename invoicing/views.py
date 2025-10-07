from django.views.generic import ListView
from .models import Invoice
from workspaces.mixins import OrganizationPermissionMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from subscriptions.decorators import subscription_required
from django.utils.decorators import method_decorator

@method_decorator(subscription_required('Pro'), name='dispatch')
class InvoiceListView(LoginRequiredMixin, OrganizationPermissionMixin, ListView):
    model = Invoice
    template_name = 'invoicing/invoice_list.html'
    context_object_name = 'invoices'
