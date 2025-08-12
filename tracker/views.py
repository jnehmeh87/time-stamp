from django.shortcuts import render, redirect
from django.views.generic import UpdateView, ListView, CreateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.utils import timezone
from django.urls import reverse_lazy
from .models import TimeEntry, Project
from .forms import TimeEntryUpdateForm

class HomePageView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        active_entry = TimeEntry.objects.filter(user=request.user, end_time__isnull=True).first()
        # The original unauthenticated view is now implicitly handled by LoginRequiredMixin
        # which redirects to the login page.
        return render(request, 'home.html', {'active_entry': active_entry})

def start_timer(request):
    if request.method == 'POST':
        # Ensure no other timer is running for the user
        if not TimeEntry.objects.filter(user=request.user, end_time__isnull=True).exists():
            TimeEntry.objects.create(user=request.user, start_time=timezone.now(), title="New Entry")
    return redirect('tracker:home')

def stop_timer(request):
    if request.method == 'POST':
        active_entry = TimeEntry.objects.filter(user=request.user, end_time__isnull=True).first()
        if active_entry:
            active_entry.end_time = timezone.now()
            active_entry.save()
            return redirect('tracker:entry_update', pk=active_entry.pk)
    return redirect('tracker:home')

class TimeEntryListView(LoginRequiredMixin, ListView):
    model = TimeEntry
    template_name = 'tracker/timeentry_list.html'
    context_object_name = 'entries'

    def get_queryset(self):
        # Return user's entries, newest first, excluding any active timer
        return TimeEntry.objects.filter(user=self.request.user, end_time__isnull=False).order_by('-start_time')

class TimeEntryUpdateView(LoginRequiredMixin, UpdateView):
    model = TimeEntry
    form_class = TimeEntryUpdateForm
    template_name = 'tracker/timeentry_form.html'
    success_url = reverse_lazy('tracker:home')

    def get_queryset(self):
        # Ensure users can only edit their own entries
        return TimeEntry.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'tracker/project_list.html'
    context_object_name = 'projects'

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user)

class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    fields = ['name', 'description']
    template_name = 'tracker/project_form.html'
    success_url = reverse_lazy('tracker:project_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    fields = ['name', 'description']
    template_name = 'tracker/project_form.html'
    success_url = reverse_lazy('tracker:project_list')

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user)

class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = 'tracker/project_confirm_delete.html'
    success_url = reverse_lazy('tracker:project_list')

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user)
