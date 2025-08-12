from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import UpdateView, ListView, CreateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from django.urls import reverse_lazy
from .models import TimeEntry, Project
from .forms import TimeEntryUpdateForm, ReportForm
from datetime import timedelta

class HomePageView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        active_entry = TimeEntry.objects.filter(user=request.user, end_time__isnull=True).first()
        # The original unauthenticated view is now implicitly handled by LoginRequiredMixin
        # which redirects to the login page.
        return render(request, 'home.html', {'active_entry': active_entry})

@login_required
def start_timer(request):
    if request.method == 'POST':
        with transaction.atomic():
            if not TimeEntry.objects.select_for_update().filter(user=request.user, end_time__isnull=True).exists():
                TimeEntry.objects.create(user=request.user, start_time=timezone.now(), title="New Entry")
    return redirect('tracker:home')

@login_required
def stop_timer(request):
    if request.method == 'POST':
        with transaction.atomic():
            active_entry = TimeEntry.objects.select_for_update().filter(user=request.user, end_time__isnull=True).first()
            if active_entry:
                active_entry.end_time = timezone.now()
                active_entry.full_clean()
                active_entry.save()
                return redirect('tracker:entry_update', pk=active_entry.pk)
    return redirect('tracker:home')

@login_required
def toggle_entry_archive(request, pk):
    if request.method == 'POST':
        entry = get_object_or_404(TimeEntry, pk=pk, user=request.user)
        entry.is_archived = not entry.is_archived
        entry.save()
    return redirect('tracker:entry_list')


class ReportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        form = ReportForm(user=request.user)
        return render(request, 'tracker/report_form.html', {'form': form})

    def post(self, request, *args, **kwargs):
        form = ReportForm(request.POST, user=request.user)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            project = form.cleaned_data.get('project')

            entries = TimeEntry.objects.filter(
                user=request.user,
                start_time__date__gte=start_date,
                end_time__date__lte=end_date,
                end_time__isnull=False
            )

            if project:
                entries = entries.filter(project=project)

            total_duration = sum([entry.duration for entry in entries if entry.duration], timedelta())

            # Format total_duration into a readable string HH:MM:SS
            total_seconds = int(total_duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            formatted_total_duration = f'{hours:02}:{minutes:02}:{seconds:02}'

            context = {
                'form': form,
                'entries': entries,
                'total_duration': formatted_total_duration,
                'start_date': start_date,
                'end_date': end_date,
                'project': project,
            }
            return render(request, 'tracker/report_form.html', context)

        return render(request, 'tracker/report_form.html', {'form': form})


class TimeEntryListView(LoginRequiredMixin, ListView):
    model = TimeEntry
    template_name = 'tracker/timeentry_list.html'
    context_object_name = 'entries'
    paginate_by = 20

    def get_queryset(self):
        queryset = TimeEntry.objects.filter(user=self.request.user, end_time__isnull=False)

        # Filtering logic
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        category = self.request.GET.get('category')
        show_archived = self.request.GET.get('show_archived')

        if start_date:
            queryset = queryset.filter(start_time__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_time__date__lte=end_date)
        if category:
            queryset = queryset.filter(category=category)
        
        if not show_archived:
            queryset = queryset.filter(is_archived=False)

        return queryset.order_by('-start_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = self.request.GET
        return context

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
