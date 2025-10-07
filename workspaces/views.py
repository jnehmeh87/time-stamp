from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy, reverse
from .models import TimeEntry, Project, TimeEntryImage
from .forms import ProjectForm, TimeEntryManualForm
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from datetime import timedelta
from .utils import format_duration_hms

# --- Project Views ---

class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'workspaces/project_list.html'
    context_object_name = 'projects'

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user)

class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'workspaces/project_form.html'
    success_url = reverse_lazy('workspaces:project_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'workspaces/project_form.html'
    success_url = reverse_lazy('workspaces:project_list')

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = 'workspaces/project_confirm_delete.html'
    success_url = reverse_lazy('workspaces:project_list')

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

# --- Time Entry Views ---

class TimeEntryListView(LoginRequiredMixin, ListView):
    model = TimeEntry
    template_name = 'workspaces/timeentry_list.html'
    context_object_name = 'entries'
    paginate_by = 15

    def get_paginate_by(self, queryset):
        filter_keys = ['start_date', 'end_date', 'category', 'project', 'show_archived']
        if any(self.request.GET.get(key) for key in filter_keys):
            return None
        return self.paginate_by

    def get_queryset(self):
        queryset = super().get_queryset().filter(user=self.request.user)
        # ... (rest of the queryset logic from tracker/views.py) ...
        return queryset

class TimeEntryCreateView(LoginRequiredMixin, CreateView):
    model = TimeEntry
    form_class = TimeEntryManualForm
    template_name = 'workspaces/timeentry_create_form.html'
    success_url = reverse_lazy('workspaces:time_entry_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.is_manual = True
        form.instance.was_edited = False
        response = super().form_valid(form)
        for image_file in self.request.FILES.getlist('images'):
            TimeEntryImage.objects.create(time_entry=self.object, image=image_file)
        return response

class TimeEntryUpdateView(LoginRequiredMixin, UpdateView):
    model = TimeEntry
    form_class = TimeEntryManualForm
    template_name = 'workspaces/timeentry_update_form.html'
    success_url = reverse_lazy('workspaces:time_entry_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def form_valid(self, form):
        time_details_were_edited = self.request.POST.get('time_details_edited_flag') == 'true'
        if time_details_were_edited:
            form.instance.was_edited = True
        response = super().form_valid(form)
        for image_file in self.request.FILES.getlist('images'):
            TimeEntryImage.objects.create(time_entry=self.object, image=image_file)
        return response

class TimeEntryDeleteView(LoginRequiredMixin, DeleteView):
    model = TimeEntry
    template_name = 'workspaces/timeentry_confirm_delete.html'
    success_url = reverse_lazy('workspaces:time_entry_list')

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

# --- Bulk Action Views ---

@login_required
def time_entry_bulk_delete_confirm(request):
    selected_ids = request.POST.getlist('selected_entries')
    preserved_filters = request.POST.get('preserved_filters', '')
    entries_to_delete = TimeEntry.objects.filter(user=request.user, pk__in=selected_ids)
    context = {
        'entries_to_delete': entries_to_delete,
        'preserved_filters': preserved_filters
    }
    return render(request, 'workspaces/timeentry_confirm_delete.html', context)

@login_required
def time_entry_bulk_delete(request):
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_entries')
        preserved_filters = request.POST.get('preserved_filters', '')
        if selected_ids:
            TimeEntry.objects.filter(user=request.user, pk__in=selected_ids).delete()
            messages.success(request, 'Selected time entries have been deleted.')
        base_url = reverse('workspaces:time_entry_list')
        if preserved_filters:
            return redirect(f'{base_url}?{preserved_filters}')
        return redirect(base_url)
    return redirect('workspaces:time_entry_list')

@login_required
def time_entry_bulk_archive_confirm(request):
    selected_ids = request.POST.getlist('selected_entries')
    preserved_filters = request.POST.get('preserved_filters', '')
    entries_to_process = TimeEntry.objects.filter(user=request.user, pk__in=selected_ids)
    context = {
        'entries_to_process': entries_to_process,
        'action': 'archive',
        'preserved_filters': preserved_filters
    }
    return render(request, 'workspaces/timeentry_confirm_archive.html', context)

@login_required
def time_entry_bulk_unarchive_confirm(request):
    selected_ids = request.POST.getlist('selected_entries')
    preserved_filters = request.POST.get('preserved_filters', '')
    entries_to_process = TimeEntry.objects.filter(user=request.user, pk__in=selected_ids)
    context = {
        'entries_to_process': entries_to_process,
        'preserved_filters': preserved_filters
    }
    return render(request, 'workspaces/timeentry_confirm_unarchive.html', context)

@login_required
def time_entry_bulk_archive(request):
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_entries')
        action = request.POST.get('action')
        preserved_filters = request.POST.get('preserved_filters', '')
        if selected_ids and action in ['archive', 'unarchive']:
            is_archived_status = (action == 'archive')
            updated_count = TimeEntry.objects.filter(user=request.user, pk__in=selected_ids).update(is_archived=is_archived_status)
            messages.success(request, f'{updated_count} selected entries have been {action}d.')
        base_url = reverse('workspaces:time_entry_list')
        if preserved_filters:
            return redirect(f'{base_url}?{preserved_filters}')
        return redirect(base_url)
    return redirect('workspaces:time_entry_list')

@login_required
def time_entry_toggle_archive(request, pk):
    if request.method == 'POST':
        entry = get_object_or_404(TimeEntry, pk=pk, user=request.user)
        entry.is_archived = not entry.is_archived
        entry.save()
        messages.success(request, f"Entry '{entry.title}' has been {'archived' if entry.is_archived else 'unarchived'}.")
    return redirect('workspaces:time_entry_list')

# --- AJAX Views ---

@login_required
def get_time_entry_details(request, pk):
    try:
        entry = TimeEntry.objects.select_related('project').prefetch_related('images').get(pk=pk, user=request.user)
        images = [{'url': img.image.url, 'id': img.id} for img in entry.images.all()]
        worked_duration = timedelta(0)
        if entry.end_time:
            gross_duration = entry.end_time - entry.start_time
            if gross_duration > entry.paused_duration:
                worked_duration = gross_duration - entry.paused_duration
        formatted_duration = format_duration_hms(worked_duration)
        formatted_paused_duration = format_duration_hms(entry.paused_duration)
        data = {
            'success': True,
            'title': entry.title,
            'project': entry.project.name if entry.project else 'No Project',
            'category': entry.get_category_display(),
            'date': entry.start_time.strftime('%b %-d, %Y'),
            'start_time': entry.start_time.strftime('%-I:%M:%S %p'),
            'end_time': entry.end_time.strftime('%-I:%M:%S %p') if entry.end_time else 'In Progress',
            'duration': formatted_duration,
            'paused_duration': formatted_paused_duration,
            'description': entry.description or 'No description provided.',
            'notes': entry.notes or 'No notes provided.',
            'images': images,
            'update_url': reverse('workspaces:time_entry_update', kwargs={'pk': entry.pk}),
        }
        return JsonResponse(data)
    except TimeEntry.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Entry not found.'}, status=404)

@login_required
def delete_time_entry_image(request, pk):
    if request.method == 'POST':
        try:
            image = TimeEntryImage.objects.get(pk=pk, time_entry__user=request.user)
            image.delete()
            return JsonResponse({'success': True})
        except TimeEntryImage.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Image not found.'}, status=404)
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=400)

@login_required
def get_projects_for_category(request):
    category = request.GET.get('category')
    projects = Project.objects.filter(user=request.user)
    if category:
        projects = projects.filter(category=category)
    project_list = list(projects.values('id', 'name'))
    return JsonResponse(project_list, safe=False)
