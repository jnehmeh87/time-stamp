from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy, reverse
from .models import TimeEntry, Project, TimeEntryImage, Contact
from .forms import ProjectForm, TimeEntryManualForm, ClientForm, CategoryForm
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from datetime import timedelta
from .utils import format_duration_hms
from django.db import transaction
from django.utils import timezone
from .mixins import OrganizationPermissionMixin

class HomePageView(View):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            active_entry = TimeEntry.objects.filter(user=request.user, end_time__isnull=True).first()
            projects = Project.objects.filter(organization__members=request.user)
            recent_entries = TimeEntry.objects.filter( 
                user=request.user, 
                end_time__isnull=False
            ).select_related('project').order_by('-start_time')[:10]

            context = {
                'active_entry': active_entry,
                'projects': projects,
                'recent_entries': recent_entries,
                'new_project_id': request.GET.get('new_project_id'),
            }
            return render(request, 'home.html', context)
        else:
            return render(request, 'tracker/landing.html')

@login_required
def start_timer(request):
    if request.method == 'POST':
        title = request.POST.get('title', 'New Entry')
        project_id = request.POST.get('project')

        project = None
        if project_id:
            project = get_object_or_404(Project, pk=project_id, organization__members=request.user)

        with transaction.atomic():
            if not TimeEntry.objects.select_for_update().filter(user=request.user, end_time__isnull=True).exists():
                TimeEntry.objects.create(
                    user=request.user,
                    start_time=timezone.now(),
                    title=title,
                    project=project,
                )
    return redirect('workspaces:home')

@login_required
def stop_timer(request):
    if request.method == 'POST':
        with transaction.atomic():
            active_entry = TimeEntry.objects.select_for_update().filter(user=request.user, end_time__isnull=True).first()
            if active_entry:
                if active_entry.is_paused and active_entry.last_pause_time:
                    pause_duration = timezone.now() - active_entry.last_pause_time
                    active_entry.paused_duration += pause_duration
                    active_entry.is_paused = False
                    active_entry.last_pause_time = None

                active_entry.end_time = timezone.now()
                active_entry.full_clean()
                active_entry.save()
                return redirect('workspaces:time_entry_update', pk=active_entry.pk)
    return redirect('workspaces:home')

@login_required
def pause_timer(request):
    if request.method == 'POST':
        with transaction.atomic():
            active_entry = TimeEntry.objects.select_for_update().filter(user=request.user, end_time__isnull=True, is_paused=False).first()
            if active_entry:
                active_entry.is_paused = True
                active_entry.last_pause_time = timezone.now()
                active_entry.save()
    return redirect('workspaces:home')

@login_required
def resume_timer(request):
    if request.method == 'POST':
        with transaction.atomic():
            active_entry = TimeEntry.objects.select_for_update().filter(user=request.user, end_time__isnull=True, is_paused=True).first()
            if active_entry and active_entry.last_pause_time:
                pause_duration = timezone.now() - active_entry.last_pause_time
                active_entry.paused_duration += pause_duration
                active_entry.is_paused = False
                active_entry.last_pause_time = None
                active_entry.save()
    return redirect('workspaces:home')

@login_required
def session_keep_alive(request):
    return JsonResponse({'success': True})

# --- Project Views ---

class ProjectListView(LoginRequiredMixin, OrganizationPermissionMixin, ListView):
    model = Project
    template_name = 'workspaces/project_list.html'
    context_object_name = 'projects'

class ProjectCreateView(LoginRequiredMixin, OrganizationPermissionMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'workspaces/project_form.html'
    success_url = reverse_lazy('workspaces:project_list')

    def form_valid(self, form):
        form.instance.organization = self.request.user.organizations.first()
        return super().form_valid(form)

class ProjectUpdateView(LoginRequiredMixin, OrganizationPermissionMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'workspaces/project_form.html'
    success_url = reverse_lazy('workspaces:project_list')

class ProjectDeleteView(LoginRequiredMixin, OrganizationPermissionMixin, DeleteView):
    model = Project
    template_name = 'workspaces/project_confirm_delete.html'
    success_url = reverse_lazy('workspaces:project_list')

@login_required
def project_toggle_archive(request, pk):
    if request.method == 'POST':
        project = get_object_or_404(Project, pk=pk, organization__members=request.user)
        project.is_archived = not project.is_archived
        project.save()
        messages.success(request, f"Project '{project.name}' has been {'archived' if project.is_archived else 'unarchived'}.")
    return redirect('workspaces:project_list')

# --- Time Entry Views ---

class TimeEntryListView(LoginRequiredMixin, OrganizationPermissionMixin, ListView):
    model = TimeEntry
    template_name = 'workspaces/timeentry_list.html'
    context_object_name = 'entries'
    paginate_by = 15

    def get_paginate_by(self, queryset):
        filter_keys = ['start_date', 'end_date', 'project', 'show_archived']
        if any(self.request.GET.get(key) for key in filter_keys):
            return None
        return self.paginate_by

class TimeEntryCreateView(LoginRequiredMixin, OrganizationPermissionMixin, CreateView):
    model = TimeEntry
    form_class = TimeEntryManualForm
    template_name = 'workspaces/timeentry_create_form.html'
    success_url = reverse_lazy('workspaces:time_entry_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.is_manual = True
        form.instance.was_edited = False
        response = super().form_valid(form)
        for image_file in self.request.FILES.getlist('images'):
            TimeEntryImage.objects.create(time_entry=self.object, image=image_file)
        return response

class TimeEntryUpdateView(LoginRequiredMixin, OrganizationPermissionMixin, UpdateView):
    model = TimeEntry
    form_class = TimeEntryManualForm
    template_name = 'workspaces/timeentry_update_form.html'
    success_url = reverse_lazy('workspaces:time_entry_list')

    def form_valid(self, form):
        time_details_were_edited = self.request.POST.get('time_details_edited_flag') == 'true'
        if time_details_were_edited:
            form.instance.was_edited = True
        response = super().form_valid(form)
        for image_file in self.request.FILES.getlist('images'):
            TimeEntryImage.objects.create(time_entry=self.object, image=image_file)
        return response

class TimeEntryDeleteView(LoginRequiredMixin, OrganizationPermissionMixin, DeleteView):
    model = TimeEntry
    template_name = 'workspaces/timeentry_confirm_delete.html'
    success_url = reverse_lazy('workspaces:time_entry_list')

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
    projects = Project.objects.filter(organization__members=request.user)
    if category:
        projects = projects.filter(contact__name=category)
    project_list = list(projects.values('id', 'name'))
    return JsonResponse(project_list, safe=False)

class ManageContactsView(LoginRequiredMixin, OrganizationPermissionMixin, View):
    def get(self, request, *args, **kwargs):
        client_form = ClientForm()
        category_form = CategoryForm()
        clients = Contact.objects.filter(organization=request.user.organizations.first(), contact_type='CLIENT')
        categories = Contact.objects.filter(organization=request.user.organizations.first(), contact_type='CATEGORY')
        context = {
            'client_form': client_form,
            'category_form': category_form,
            'clients': clients,
            'categories': categories,
        }
        return render(request, 'workspaces/manage_contacts.html', context)

    def post(self, request, *args, **kwargs):
        if 'submit_client' in request.POST:
            form = ClientForm(request.POST)
            if form.is_valid():
                contact = form.save(commit=False)
                contact.organization = request.user.organizations.first()
                contact.contact_type = 'CLIENT'
                contact.save()
                messages.success(request, 'Client created successfully.')
                return redirect('workspaces:manage_contacts')
        elif 'submit_category' in request.POST:
            form = CategoryForm(request.POST)
            if form.is_valid():
                contact = form.save(commit=False)
                contact.organization = request.user.organizations.first()
                contact.contact_type = 'CATEGORY'
                contact.save()
                messages.success(request, 'Category created successfully.')
                return redirect('workspaces:manage_contacts')
        
        # if form is not valid
        client_form = ClientForm()
        category_form = CategoryForm()
        if 'submit_client' in request.POST:
            client_form = form
        elif 'submit_category' in request.POST:
            category_form = form
            
        clients = Contact.objects.filter(organization=request.user.organizations.first(), contact_type='CLIENT')
        categories = Contact.objects.filter(organization=request.user.organizations.first(), contact_type='CATEGORY')
        context = {
            'client_form': client_form,
            'category_form': category_form,
            'clients': clients,
            'categories': categories,
        }
        return render(request, 'workspaces/manage_contacts.html', context)
