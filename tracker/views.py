from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from django.urls import reverse_lazy, reverse
from urllib.parse import urlencode
from .models import TimeEntry, Project, TimeEntryImage
from .forms import TimeEntryForm, ProjectForm, TimeEntryFilterForm, ReportForm, TimeEntryUpdateForm, UserUpdateForm, ProfileUpdateForm
from django.contrib import messages
from django.contrib.auth import logout
from django.db.models import Sum, F, ExpressionWrapper, DurationField, Min, Max, Count, Q
from django.db.models.functions import TruncDay
from django.http import JsonResponse
from datetime import timedelta, date, datetime, time
from decimal import Decimal
from collections import defaultdict
import csv
from googletrans import Translator, LANGUAGES
from .utils import render_to_pdf, format_duration_hms

# --- Home & Timer Views ---

class HomePageView(View):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            active_entry = TimeEntry.objects.filter(user=request.user, end_time__isnull=True).first()
            projects = Project.objects.filter(user=request.user)
            recent_entries = TimeEntry.objects.filter(
                user=request.user, 
                end_time__isnull=False
            ).order_by('-start_time')[:10]

            # Find the most recent project for each category
            latest_work_entry = TimeEntry.objects.filter(user=request.user, category='work', project__isnull=False).order_by('-start_time').first()
            latest_personal_entry = TimeEntry.objects.filter(user=request.user, category='personal', project__isnull=False).order_by('-start_time').first()

            context = {
                'active_entry': active_entry,
                'projects': projects,
                'recent_entries': recent_entries,
                'latest_work_project_id': latest_work_entry.project.id if latest_work_entry else None,
                'latest_personal_project_id': latest_personal_entry.project.id if latest_personal_entry else None,
                'new_project_id': request.GET.get('new_project_id'),
                'new_category': request.GET.get('new_category'),
            }
            return render(request, 'home.html', context)
        else:
            return render(request, 'tracker/landing.html')

@login_required
def start_timer(request):
    if request.method == 'POST':
        title = request.POST.get('title', 'New Entry')
        project_id = request.POST.get('project')
        category = request.POST.get('category', 'work')

        project = None
        if project_id:
            project = get_object_or_404(Project, pk=project_id, user=request.user)

        with transaction.atomic():
            if not TimeEntry.objects.select_for_update().filter(user=request.user, end_time__isnull=True).exists():
                TimeEntry.objects.create(
                    user=request.user,
                    start_time=timezone.now(),
                    title=title,
                    project=project,
                    category=category
                )
    return redirect('tracker:home')

@login_required
def stop_timer(request):
    if request.method == 'POST':
        with transaction.atomic():
            active_entry = TimeEntry.objects.select_for_update().filter(user=request.user, end_time__isnull=True).first()
            if active_entry:
                # If the timer is stopped while paused, calculate the final pause duration first
                if active_entry.is_paused and active_entry.last_pause_time:
                    pause_duration = timezone.now() - active_entry.last_pause_time
                    active_entry.paused_duration += pause_duration
                    active_entry.is_paused = False
                    active_entry.last_pause_time = None

                active_entry.end_time = timezone.now()
                active_entry.full_clean()
                active_entry.save()
                return redirect('tracker:entry_update', pk=active_entry.pk)
    return redirect('tracker:home')

@login_required
def pause_timer(request):
    if request.method == 'POST':
        with transaction.atomic():
            active_entry = TimeEntry.objects.select_for_update().filter(user=request.user, end_time__isnull=True, is_paused=False).first()
            if active_entry:
                active_entry.is_paused = True
                active_entry.last_pause_time = timezone.now()
                active_entry.save()
    return redirect('tracker:home')

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
    return redirect('tracker:home')

# --- Time Entry Views ---

class TimeEntryListView(LoginRequiredMixin, ListView):
    model = TimeEntry
    template_name = 'tracker/timeentry_list.html'
    context_object_name = 'entries'
    paginate_by = 15

    def get_paginate_by(self, queryset):
        """
        Disables pagination if any filters are applied in the request.
        """
        # These are the keys for filtering, excluding pagination and sorting controls.
        filter_keys = ['start_date', 'end_date', 'category', 'project', 'show_archived']
        
        # If any of the filter keys with a value are present in the GET request, disable pagination.
        if any(self.request.GET.get(key) for key in filter_keys):
            return None
        
        return self.paginate_by

    def get_queryset(self):
        queryset = super().get_queryset().filter(user=self.request.user)

        # Determine form data: use GET params if available, otherwise use defaults.
        form_data = self.request.GET
        if not form_data:
            today = timezone.now().date()
            start_of_month = today.replace(day=1)
            form_data = {
                'start_date': start_of_month,
                'end_date': today,
            }
        
        self.form = TimeEntryFilterForm(form_data)

        # Annotate with duration for sorting
        queryset = queryset.annotate(duration_calc=F('end_time') - F('start_time'))

        if self.form.is_valid():
            start_date = self.form.cleaned_data.get('start_date')
            if start_date:
                queryset = queryset.filter(start_time__date__gte=start_date)

            end_date = self.form.cleaned_data.get('end_date')
            if end_date:
                # Include entries that end on or before the end_date,
                # OR entries that are still running (end_time is NULL).
                queryset = queryset.filter(
                    Q(end_time__date__lte=end_date) | Q(end_time__isnull=True)
                )

            category = self.form.cleaned_data.get('category')
            if category:
                queryset = queryset.filter(category=category)

            project = self.form.cleaned_data.get('project')
            if project:
                queryset = queryset.filter(project=project)
            
            if self.form.cleaned_data.get('show_archived'):
                queryset = queryset.filter(is_archived=True)
            else:
                queryset = queryset.filter(is_archived=False)
        else:
            # Fallback for safety, though the form should always be valid with defaults.
            queryset = queryset.filter(is_archived=False)

        # Sorting logic
        sort_by = self.request.GET.get('sort_by')
        sort_dir = self.request.GET.get('sort_dir')

        # Map user-friendly sort fields to database fields
        sort_field_mapping = {
            'task': 'title',
            'project': 'project__name',
            'date': 'start_time',
            'start_time': 'start_time',
            'duration': 'duration_calc', # Use the annotated field
            'paused_time': 'paused_duration',
            'category': 'category',
        }
        
        sort_field_db = sort_field_mapping.get(sort_by)

        if sort_field_db and sort_dir in ['asc', 'desc']:
            # Apply user-specified sort
            if sort_dir == 'desc':
                sort_field_db = f'-{sort_field_db}'
            queryset = queryset.order_by(sort_field_db, '-pk')
        else:
            # Apply default sort (newest first)
            queryset = queryset.order_by('-start_time', '-pk')


        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pass the form to the template
        context['form'] = self.form

                # Pass sorting info to template
        context['sort_by'] = self.request.GET.get('sort_by', 'date')
        context['sort_dir'] = self.request.GET.get('sort_dir', 'desc')

        # Data for dynamic project dropdown
        context['all_projects'] = Project.objects.filter(user=self.request.user)
        latest_work_entry = TimeEntry.objects.filter(user=self.request.user, category='work', project__isnull=False).order_by('-start_time').first()
        latest_personal_entry = TimeEntry.objects.filter(user=self.request.user, category='personal', project__isnull=False).order_by('-start_time').first()
        context['latest_work_project_id'] = latest_work_entry.project.id if latest_work_entry else None
        context['latest_personal_project_id'] = latest_personal_entry.project.id if latest_personal_entry else None

        return context

class TimeEntryCreateView(LoginRequiredMixin, CreateView):
    model = TimeEntry
    form_class = TimeEntryUpdateForm
    template_name = 'tracker/timeentry_create_form.html' # Use the new create template
    success_url = reverse_lazy('tracker:entry_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.is_manual = True  # This is a manually created entry.
        form.instance.was_edited = False # It has not been "edited" yet.
        
        # Let the parent view handle saving the form and creating the redirect.
        response = super().form_valid(form)

        # Now that the main object is saved (as self.object), handle image uploads.
        for image_file in self.request.FILES.getlist('images'):
            TimeEntryImage.objects.create(time_entry=self.object, image=image_file)
            
        return response

class TimeEntryUpdateView(LoginRequiredMixin, UpdateView):
    model = TimeEntry
    form_class = TimeEntryUpdateForm
    template_name = 'tracker/timeentry_update_form.html' # Use the new update template
    success_url = reverse_lazy('tracker:entry_list')

    def get_object(self, queryset=None):
        # We no longer need to store original values here.
        return super().get_object(queryset)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def form_valid(self, form):
        # Check the hidden input flag from the POST data.
        time_details_were_edited = self.request.POST.get('time_details_edited_flag') == 'true'

        # Set the flag ONLY if the user explicitly edited the time details.
        # Do not touch the is_manual flag here.
        if time_details_were_edited:
            form.instance.was_edited = True

        # Let the parent view handle saving the form and creating the redirect response.
        # This also sets self.object for us to use.
        response = super().form_valid(form)

        # Now that the main object is saved, handle the image uploads.
        for image_file in self.request.FILES.getlist('images'):
            TimeEntryImage.objects.create(time_entry=self.object, image=image_file)
            
        return response

class TimeEntryDeleteView(LoginRequiredMixin, DeleteView):
    model = TimeEntry
    template_name = 'tracker/timeentry_confirm_delete_single.html'
    success_url = reverse_lazy('tracker:entry_list')

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
    return render(request, 'tracker/timeentry_confirm_delete.html', context)

@login_required
def time_entry_bulk_delete(request):
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_entries')
        preserved_filters = request.POST.get('preserved_filters', '')
        if selected_ids:
            TimeEntry.objects.filter(user=request.user, pk__in=selected_ids).delete()
            messages.success(request, 'Selected time entries have been deleted.')
        
        base_url = reverse('tracker:entry_list')
        if preserved_filters:
            return redirect(f'{base_url}?{preserved_filters}')
        return redirect(base_url)
    return redirect('tracker:entry_list')

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
    return render(request, 'tracker/timeentry_confirm_archive.html', context)

@login_required
def time_entry_bulk_unarchive_confirm(request):
    selected_ids = request.POST.getlist('selected_entries')
    preserved_filters = request.POST.get('preserved_filters', '')
    entries_to_process = TimeEntry.objects.filter(user=request.user, pk__in=selected_ids)
    context = {
        'entries_to_process': entries_to_process,
        'preserved_filters': preserved_filters
    }
    return render(request, 'tracker/timeentry_confirm_unarchive.html', context)

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

        base_url = reverse('tracker:entry_list')
        if preserved_filters:
            return redirect(f'{base_url}?{preserved_filters}')
        return redirect(base_url)
    return redirect('tracker:entry_list')

@login_required
def time_entry_toggle_archive(request, pk):
    entry = get_object_or_404(TimeEntry, pk=pk, user=request.user)
    entry.is_archived = not entry.is_archived
    entry.save()
    messages.success(request, f"Entry '{entry.title}' has been {'archived' if entry.is_archived else 'unarchived'}.")
    return redirect('tracker:entry_list')

# --- Project Views ---

class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'tracker/project_list.html'
    context_object_name = 'projects'

    def get_queryset(self):
        queryset = super().get_queryset().filter(user=self.request.user)
        if not self.request.GET.get('show_archived'):
            queryset = queryset.filter(is_archived=False)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_projects = context['projects']
        context['work_projects'] = all_projects.filter(category='work')
        context['personal_projects'] = all_projects.filter(category='personal')
        context['show_archived'] = self.request.GET.get('show_archived', False)
        return context

class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'tracker/project_form.html'
    success_url = reverse_lazy('tracker:project_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        self.object = form.save()
        next_url = self.request.GET.get('next')
        if next_url:
            params = urlencode({
                'new_project_id': self.object.pk,
                'new_category': self.object.category
            })
            return redirect(f"{next_url}?{params}")
        return super().form_valid(form)

class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'tracker/project_form.html'
    success_url = reverse_lazy('tracker:project_list')

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = 'tracker/project_confirm_delete.html'
    success_url = reverse_lazy('tracker:project_list')

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

@login_required
def project_archive_confirm(request, pk):
    project = get_object_or_404(Project, pk=pk, user=request.user)
    return render(request, 'tracker/project_confirm_archive.html', {'project': project})

@login_required
def project_unarchive_confirm(request, pk):
    project = get_object_or_404(Project, pk=pk, user=request.user)
    return render(request, 'tracker/project_confirm_unarchive.html', {'project': project})

@login_required
def project_toggle_archive(request, pk):
    project = get_object_or_404(Project, pk=pk, user=request.user)
    
    if request.method == 'POST':
        # Toggle the project's archive status
        new_status = not project.is_archived
        project.is_archived = new_status
        project.save()

        # Handle cascading archive if the user requested it
        if new_status and request.POST.get('archive_entries'):
            project.time_entries.update(is_archived=True)
            messages.success(request, f"Project '{project.name}' and its time entries have been archived.")
        # Handle cascading unarchive
        elif not new_status and request.POST.get('unarchive_entries'):
            project.time_entries.update(is_archived=False)
            messages.success(request, f"Project '{project.name}' and its time entries have been unarchived.")
        else:
            action = 'archived' if new_status else 'unarchived'
            messages.success(request, f"Project '{project.name}' has been {action}.")
            
    return redirect('tracker:project_list')


# --- AJAX Views ---

@login_required
def get_time_entry_details(request, pk):
    try:
        entry = TimeEntry.objects.select_related('project').prefetch_related('images').get(pk=pk, user=request.user)
        images = [{'url': img.image.url, 'id': img.id} for img in entry.images.all()]
        
        # --- Correctly calculate and format durations ---
        worked_duration = timedelta(0)
        if entry.end_time:
            gross_duration = entry.end_time - entry.start_time
            # Ensure worked duration is not negative
            if gross_duration > entry.paused_duration:
                worked_duration = gross_duration - entry.paused_duration
        
        formatted_duration = format_duration_hms(worked_duration)
        formatted_paused_duration = format_duration_hms(entry.paused_duration)
        # --- End of formatting ---

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
            'update_url': reverse('tracker:entry_update', kwargs={'pk': entry.pk}),
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

@login_required
def get_project_dates(request):
    project_id = request.GET.get('project_id')
    if project_id:
        project = get_object_or_404(Project, pk=project_id, user=request.user)
        dates = TimeEntry.objects.filter(project=project, user=request.user).aggregate(
            start_date=Min('start_time__date'),
            end_date=Max('end_time__date')
        )
        if dates['start_date'] and dates['end_date']:
            return JsonResponse({
                'success': True,
                'start_date': dates['start_date'].strftime('%Y-%m-%d'),
                'end_date': dates['end_date'].strftime('%Y-%m-%d'),
            })
    return JsonResponse({'success': False})

# --- Report and Translation Views ---

class AnalyticsDashboardView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        user = request.user
        
        # --- Date Range and Category Filtering ---
        period = request.GET.get('period', '30d')
        category = request.GET.get('category') # Get category from request
        end_date = timezone.now()
        start_date = None
        days_in_period = 30

        if period == '7d':
            start_date = end_date - timedelta(days=7)
            days_in_period = 7
        elif period == '15d':
            start_date = end_date - timedelta(days=15)
            days_in_period = 15
        elif period == '3m':
            start_date = end_date - timedelta(days=90)
            days_in_period = 90
        elif period == '6m':
            start_date = end_date - timedelta(days=182)
            days_in_period = 182
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
            days_in_period = 365
        elif period == 'all':
            start_date = None
        else: # Default to 30d
            period = '30d'
            start_date = end_date - timedelta(days=30)

        # --- Main Queryset ---
        time_entries_qs = TimeEntry.objects.filter(user=user, end_time__isnull=False)
        if start_date:
            time_entries_qs = time_entries_qs.filter(start_time__gte=start_date)
        
        # Apply category filter to the main queryset if provided
        if category and category != 'all':
            time_entries_qs = time_entries_qs.filter(project__category=category)

        # --- 4. Line Chart: Activity by Project over selected period ---
        # (This logic will now run with the filtered queryset)
        
        # Determine date range for labels
        label_start_date = start_date
        if period == 'all':
            first_entry = TimeEntry.objects.filter(user=user, end_time__isnull=False).order_by('start_time').first()
            if first_entry:
                label_start_date = first_entry.start_time
                days_in_period = (timezone.now().date() - label_start_date.date()).days + 1
            else: # No entries at all
                label_start_date = timezone.now()
                days_in_period = 1
        
        activity_labels = [(label_start_date.date() + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days_in_period)]
        
        # Group data by project
        activity_by_project = defaultdict(lambda: {day: 0 for day in activity_labels})
        
        # Get a list of all projects in the period to ensure they appear in the legend
        projects_in_period = time_entries_qs.filter(project__name__isnull=False).values_list('project__name', flat=True).distinct()
        projects = sorted(list(projects_in_period))

        # Fetch entries to process in Python, splitting them if they cross midnight
        entries_for_chart = time_entries_qs.select_related('project')

        for entry in entries_for_chart:
            project_name = entry.project.name if entry.project else 'Unassigned'
            
            current_time = entry.start_time
            while current_time < entry.end_time:
                day_str = current_time.strftime('%Y-%m-%d')
                
                # Midnight of the current day
                midnight = timezone.make_aware(
                    datetime.combine(current_time.date() + timedelta(days=1), time.min),
                    current_time.tzinfo
                )
                
                chunk_end = min(midnight, entry.end_time)
                duration = chunk_end - current_time
                
                if day_str in activity_by_project[project_name]:
                    activity_by_project[project_name][day_str] += duration.total_seconds() / 3600
                
                current_time = chunk_end

        activity_datasets = []
        if time_entries_qs.filter(project__isnull=True).exists() and 'Unassigned' not in projects:
             projects.insert(0, 'Unassigned')

        for project_name in projects:
            # Only add dataset if there's data for it
            if project_name in activity_by_project and any(activity_by_project[project_name].values()):
                dataset = {
                    'label': project_name,
                    'data': [activity_by_project[project_name][day] for day in activity_labels]
                }
                activity_datasets.append(dataset)

        # --- AJAX Request Handling ---
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'activity_chart_labels': activity_labels,
                'activity_chart_datasets': activity_datasets,
            })

        # --- Full Page Load Context ---
        # The rest of the data is calculated only for a full page load
        
        # --- 1. Summary Cards Data ---
        # Recalculate summary without category filter for the top cards
        summary_qs = TimeEntry.objects.filter(user=user, end_time__isnull=False)
        if start_date:
            summary_qs = summary_qs.filter(start_time__gte=start_date)
            
        work_duration = summary_qs.filter(category='work').aggregate(total=Sum(F('end_time') - F('start_time')))['total'] or timedelta()
        personal_duration = summary_qs.filter(category='personal').aggregate(total=Sum(F('end_time') - F('start_time')))['total'] or timedelta()

        # Calculate total earnings only from projects with an hourly rate > 0
        earnings_entries = summary_qs.filter(project__hourly_rate__gt=0)
        total_earnings = sum(
            (entry.duration.total_seconds() / 3600) * float(entry.project.hourly_rate)
            for entry in earnings_entries
        )

        # --- 2. Doughnut Chart: Time per Category ---
        time_per_category_chart = summary_qs.values('category').annotate(
            duration_seconds=Sum(F('end_time') - F('start_time'))
        ).order_by('-duration_seconds')

        category_chart_labels = [item['category'].capitalize() if item['category'] else 'Unassigned' for item in time_per_category_chart]
        category_chart_data = [item['duration_seconds'].total_seconds() / 3600 for item in time_per_category_chart]

        # --- 3. Bar Chart: Earnings per Project ---
        earnings_per_project = earnings_entries.values('project__name').annotate(
            total_seconds=Sum(F('end_time') - F('start_time')),
            hourly_rate=F('project__hourly_rate')
        ).order_by('-total_seconds')

        earnings_labels = [item['project__name'] for item in earnings_per_project]
        earnings_data = [
            (item['total_seconds'].total_seconds() / 3600) * float(item['hourly_rate'])
            for item in earnings_per_project
        ]

        context = {
            'work_duration': work_duration,
            'personal_duration': personal_duration,
            'total_earnings': total_earnings,
            'active_period': period,
            'active_category': category, # Pass active category to template
            
            'category_chart_labels': category_chart_labels,
            'category_chart_data': category_chart_data,

            'earnings_chart_labels': earnings_labels,
            'earnings_chart_data': earnings_data,

            'activity_chart_labels': activity_labels,
            'activity_chart_datasets': activity_datasets,
        }
        return render(request, 'tracker/analytics.html', context)

class ReportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        form = ReportForm(request.GET or None, user=request.user)
        context = {'form': form, 'entries': None}

        # Set default dates only if the form is not submitted
        if not request.GET:
            today = date.today()
            start_of_month = today.replace(day=1)
            form.initial = {
                'start_date': start_of_month,
                'end_date': today,
            }
            # Re-render the form with initial data
            context['form'] = ReportForm(initial=form.initial, user=request.user)
            return render(request, 'tracker/report_form.html', context)

        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            project = form.cleaned_data.get('project')
            category = form.cleaned_data.get('category')
            export_format = request.GET.get('export')

            entries = TimeEntry.objects.filter(
                user=request.user,
                start_time__date__gte=start_date,
                end_time__date__lte=end_date,
                end_time__isnull=False,
                is_archived=False  # <-- Add this line
            ).select_related('project')

            if project:
                entries = entries.filter(project=project)
            elif category:
                entries = entries.filter(project__category=category)

            # Pre-format durations for the PDF context
            for entry in entries:
                if entry.duration:
                    total_seconds = int(entry.duration.total_seconds())
                    hours, remainder = divmod(total_seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    entry.formatted_duration = f'{hours:02}:{minutes:02}:{seconds:02}'
                else:
                    entry.formatted_duration = "00:00:00"

            total_duration_val = sum([entry.duration for entry in entries if entry.duration], timedelta())
            
            total_seconds = int(total_duration_val.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            formatted_total_duration = f'{hours:02}:{minutes:02}:{seconds:02}'

            context.update({
                'entries': entries,
                'total_duration': formatted_total_duration,
                'start_date': start_date,
                'end_date': end_date,
                'project': project,
                'request': request,
            })

            if export_format == 'csv':
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="time_report_{start_date}_to_{end_date}.csv"'
                writer = csv.writer(response)
                writer.writerow(['Title', 'Project', 'Start Time', 'End Time', 'Duration (HH:MM:SS)', 'Category', 'Description', 'Notes'])
                for entry in entries:
                    writer.writerow([
                        entry.title,
                        entry.project.name if entry.project else '-',
                        entry.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                        entry.end_time.strftime('%Y-%m-%d %H:%M:%S') if entry.end_time else '',
                        str(entry.duration),
                        entry.get_category_display(),
                        entry.description,
                        entry.notes,
                    ])
                return response
            
            if export_format == 'pdf':
                pdf = render_to_pdf('tracker/report_untranslated_pdf.html', context)
                if pdf:
                    response = HttpResponse(pdf, content_type='application/pdf')
                    filename = f"report_{start_date}_to_{end_date}.pdf"
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    return response

            # Use the already calculated total_duration for the HTML view
            context['total_duration'] = total_duration_val
        
        return render(request, 'tracker/report_form.html', context)

@login_required
def translate_report(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    project_id = request.GET.get('project')
    target_language = request.GET.get('target_language')
    export_format = request.GET.get('export')

    if not all([start_date, end_date, target_language]):
        return redirect('tracker:reports')

    entries = TimeEntry.objects.filter(
        user=request.user,
        start_time__date__gte=start_date,
        end_time__date__lte=end_date,
        end_time__isnull=False
    ).select_related('project')

    if project_id:
        entries = entries.filter(project_id=project_id)

    translator = Translator()

    # --- RTL Language Check ---
    RTL_LANGUAGES = ['ar', 'he', 'fa', 'ur']
    is_rtl = target_language in RTL_LANGUAGES

    # Get the English name of the target language and then translate it.
    target_language_english_name = LANGUAGES.get(target_language, target_language).capitalize()
    try:
        translated_language_name = translator.translate(target_language_english_name, dest=target_language).text
    except (TypeError, AttributeError):
        # If translation of the language name fails, fall back to the English name
        translated_language_name = target_language_english_name

    # Translate static text for the template
    trans_context = {
        't_translated_report': translator.translate('Translated Report', dest=target_language).text,
        't_project': translator.translate('Project', dest=target_language).text,
        't_date_range': translator.translate('Date Range', dest=target_language).text,
        't_language': translator.translate('Language', dest=target_language).text,
        't_all_projects': translator.translate('All Projects', dest=target_language).text,
        't_details': translator.translate('Details', dest=target_language).text,
        't_start_time': translator.translate('Start Time', dest=target_language).text,
        't_end_time': translator.translate('End Time', dest=target_language).text,
        't_duration': translator.translate('Duration', dest=target_language).text,
        't_description': translator.translate('Description', dest=target_language).text,
        't_notes': translator.translate('Notes', dest=target_language).text,
        't_entry': translator.translate('Entry', dest=target_language).text,
        't_no_entries': translator.translate('No entries found for this period.', dest=target_language).text,
    }

    translated_entries = []
    for entry in entries:
        translated_title = translator.translate(entry.title, dest=target_language).text if entry.title else ""
        translated_description = translator.translate(entry.description, dest=target_language).text if entry.description else ""
        translated_notes = translator.translate(entry.notes, dest=target_language).text if entry.notes else ""

        # Pre-format duration for PDF
        duration_str = ""
        if entry.duration:
            total_seconds = int(entry.duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = f'{hours:02}:{minutes:02}:{seconds:02}'

        translated_entries.append({
            'original': entry,
            'title': translated_title,
            'description': translated_description,
            'notes': translated_notes,
            'formatted_duration': duration_str,
        })
    
    project = Project.objects.filter(pk=project_id).first() if project_id else None
    
    context = {
        'entries': translated_entries,
        'start_date': start_date,
        'end_date': end_date,
        'project': project,
        'target_language': translated_language_name,
        'request': request,
        'trans': trans_context,
        'is_rtl': is_rtl,
    }

    if export_format == 'pdf':
        pdf = render_to_pdf('tracker/report_pdf.html', context)
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            filename = f"translated_report_{start_date}_to_{end_date}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="translated_report_{start_date}_to_{end_date}.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Original Title', 'Translated Title', 'Original Description', 'Translated Description',
            'Original Notes', 'Translated Notes', 'Project', 'Start Time', 'Duration (HH:MM:SS)'
        ])
        for item in translated_entries:
            entry = item['original']
            writer.writerow([
                entry.title, item['title'], entry.description, entry['description'],
                entry.notes, item['notes'], entry.project.name if entry.project else '-',
                entry.start_time.strftime('%Y-%m-%d %H:%M:%S'), str(entry.duration)
            ])
        return response

    return render(request, 'tracker/report_translated.html', context)

def daily_earnings_tracker(request):
    form = ReportForm(request.GET or None, user=request.user)
    context = {'form': form}
    project = None

    # Set default values for initial page load
    if not request.GET:
        today = date.today()
        start_of_month = today.replace(day=1)
        
        # Find the most recent 'work' project to pre-select
        latest_work_entry = TimeEntry.objects.filter(
            user=request.user, 
            project__category='work', 
            project__isnull=False
        ).order_by('-start_time').first()
        
        initial_data = {
            'start_date': start_of_month,
            'end_date': today,
            'category': 'work',
            'project': latest_work_entry.project if latest_work_entry else None,
        }
        form = ReportForm(initial=initial_data, user=request.user)
        context['form'] = form
        # Do not proceed to calculations on initial load
        return render(request, 'tracker/daily_earnings_tracker.html', context)

    if form.is_valid():
        project_id = form.cleaned_data.get('project')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')

        if project_id:
            project = project_id # The form returns a Project instance

        if project and project.hourly_rate and start_date and end_date:
            # --- Swedish Tax Constants ---
            SOCIAL_FEES_RATE = Decimal('0.2897')
            MUNICIPAL_TAX_RATE = Decimal('0.32') # Using a common average

            end_date_inclusive = end_date + timedelta(days=1)
            entries = TimeEntry.objects.filter(
                project=project,
                start_time__gte=datetime.combine(start_date, time.min),
                end_time__lt=datetime.combine(end_date, time.max), # Corrected to include full end day
                user=request.user
            ).order_by('start_time')

            hourly_rate = Decimal(project.hourly_rate)

            # Add worked_duration to each entry for the template
            total_worked_duration = timedelta(0)
            for entry in entries:
                if entry.end_time and entry.start_time:
                    # Ensure worked duration is not negative
                    duration = (entry.end_time - entry.start_time) - entry.paused_duration
                    entry.worked_duration = max(duration, timedelta(0))
                    total_worked_duration += entry.worked_duration
                else:
                    entry.worked_duration = timedelta(0)

            # Summary Calculations based on Swedish Sole Trader model
            total_hours = Decimal(total_worked_duration.total_seconds()) / Decimal(3600)
            gross_pay = total_hours * hourly_rate # This is the revenue

            social_fees_amount = gross_pay * SOCIAL_FEES_RATE
            taxable_income = gross_pay - social_fees_amount
            income_tax_amount = taxable_income * MUNICIPAL_TAX_RATE
            net_pay = taxable_income - income_tax_amount

            # Data for chart
            daily_earnings = defaultdict(Decimal)
            # Create a date range for the chart to include days with zero earnings
            all_days = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
            
            for day in all_days:
                daily_earnings[day.strftime('%Y-%m-%d')] = Decimal(0)

            for entry in entries:
                date_key = entry.start_time.strftime('%Y-%m-%d')
                worked_hours_entry = Decimal(entry.worked_duration.total_seconds()) / Decimal(3600)
                if date_key in daily_earnings:
                    daily_earnings[date_key] += worked_hours_entry * hourly_rate
            
            chart_labels = sorted(daily_earnings.keys())
            chart_data = [daily_earnings[label] for label in chart_labels]

            context.update({
                'project': project,
                'entries': entries,
                'hourly_rate': hourly_rate,
                'chart_labels': chart_labels,
                'chart_data': chart_data,
                'total_hours': total_hours,
                'gross_pay': gross_pay,
                'social_fees_amount': social_fees_amount,
                'income_tax_amount': income_tax_amount,
                'net_pay': net_pay,
            })

    return render(request, 'tracker/daily_earnings_tracker.html', context)

def income_calculator(request):
    # --- Part 1: Swedish Freelance Rate Calculator ---
    context = {}
    desired_salary_str = request.GET.get('desired_salary')

    if desired_salary_str:
        try:
            # --- Input Data ---
            desired_salary = Decimal(desired_salary_str)
            overhead_costs = Decimal(request.GET.get('overhead_costs', '0'))
            profit_margin_perc = Decimal(request.GET.get('profit_margin', '0'))
            billable_hours = Decimal(request.GET.get('billable_hours', '1')) # Avoid division by zero
            municipal_tax_perc = Decimal(request.GET.get('municipal_tax', '0'))

            # --- Constants for Swedish calculations ---
            SOCIAL_FEES_RATE = Decimal('0.2897')
            VACATION_PAY_RATE = Decimal('0.12')
            PENSION_RATE = Decimal('0.045')
            SICK_LEAVE_BUFFER_RATE = Decimal('0.05')
            STATE_TAX_THRESHOLD = Decimal('598500') # For 2023/2024, annual income
            
            # --- Calculations ---
            social_fees = desired_salary * SOCIAL_FEES_RATE
            vacation_pay = desired_salary * VACATION_PAY_RATE
            pension_savings = desired_salary * PENSION_RATE
            sick_leave_buffer = desired_salary * SICK_LEAVE_BUFFER_RATE

            total_monthly_cost = (desired_salary + social_fees + vacation_pay + 
                                  pension_savings + sick_leave_buffer + overhead_costs)
            
            profit_amount = total_monthly_cost * (profit_margin_perc / 100)
            total_to_invoice = total_monthly_cost + profit_amount
            
            hourly_rate_to_charge = total_to_invoice / billable_hours if billable_hours > 0 else 0

            # Personal take-home pay calculation
            total_tax_amount = desired_salary * (municipal_tax_perc / 100)
            # Note: This is a simplification. Real tax is more complex.
            net_salary = desired_salary - total_tax_amount

            context.update({
                'hourly_rate_to_charge': hourly_rate_to_charge,
                'desired_salary': desired_salary,
                'overhead_costs': overhead_costs,
                'profit_margin': profit_margin_perc,
                'social_fees': social_fees,
                'vacation_pay': vacation_pay,
                'pension_savings': pension_savings,
                'sick_leave_buffer': sick_leave_buffer,
                'total_monthly_cost': total_monthly_cost,
                'profit_amount': profit_amount,
                'total_to_invoice': total_to_invoice,
                'municipal_tax': municipal_tax_perc,
                'total_tax_amount': total_tax_amount,
                'net_salary': net_salary,
                'state_tax_threshold': STATE_TAX_THRESHOLD,
            })
        except (ValueError, TypeError):
            messages.error(request, "Invalid input. Please enter valid numbers.")

    return render(request, 'tracker/income_calculator.html', context)


def ajax_get_project_dates(request):
    project_id = request.GET.get('project_id')
    if project_id:
        project = get_object_or_404(Project, pk=project_id, user=request.user)
        dates = TimeEntry.objects.filter(project=project, user=request.user).aggregate(
            start_date=Min('start_time__date'),
            end_date=Max('end_time__date')
        )
        if dates['start_date'] and dates['end_date']:
            return JsonResponse({
                'success': True,
                'start_date': dates['start_date'].strftime('%Y-%m-%d'),
                'end_date': dates['end_date'].strftime('%Y-%m-%d'),
            })
    return JsonResponse({'success': False})

# --- Analytics View ---

def get_analytics_data(user, period='30d', category=None):
    # This function should contain your logic to calculate all analytics data.
    # The following is a simplified example.
    
    # Determine date range from period
    now = timezone.now()
    if period == '7d':
        start_date = now - timedelta(days=7)
    elif period == '15d':
        start_date = now - timedelta(days=15)
    # ... other periods
    else: # default to 30d
        start_date = now - timedelta(days=30)

    # Base queryset
    time_entries = TimeEntry.objects.filter(user=user, start_time__gte=start_date)
    
    # Filter by category if provided and not 'all'
    if category and category != 'all':
        time_entries = time_entries.filter(project__category=category)

    # --- Activity Chart Data ---
    activity_chart_labels = []
    # Generate labels for the period (e.g., last 30 days)
    current_date = start_date.date()
    while current_date <= now.date():
        activity_chart_labels.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)

    project_activity = defaultdict(lambda: defaultdict(float))
    for entry in time_entries:
        if entry.end_time:
            date_str = entry.start_time.strftime('%Y-%m-%d')
            duration_hours = entry.get_duration().total_seconds() / 3600
            project_activity[entry.project.name][date_str] += duration_hours

    activity_chart_datasets = []
    for project_name, date_hours in project_activity.items():
        data = [date_hours.get(date, 0) for date in activity_chart_labels]
        activity_chart_datasets.append({
            'label': project_name,
            'data': data,
        })

    # --- Other Chart Data (placeholders) ---
    # You would also calculate your other chart data here
    work_duration = timedelta(0)
    personal_duration = timedelta(0)
    total_earnings = 0
    category_chart_labels = []
    category_chart_data = []
    earnings_chart_labels = []
    earnings_chart_data = []

    return {
        'activity_chart_labels': activity_chart_labels,
        'activity_chart_datasets': activity_chart_datasets,
        'work_duration': work_duration,
        'personal_duration': personal_duration,
        'total_earnings': total_earnings,
        'category_chart_labels': category_chart_labels,
        'category_chart_data': category_chart_data,
        'earnings_chart_labels': earnings_chart_labels,
        'earnings_chart_data': earnings_chart_data,
        'active_period': period,
        'active_category': category,
    }


@login_required
def analytics_view(request):
    period = request.GET.get('period', '30d')
    category = request.GET.get('category', 'all')

    # Check if it's an AJAX request asking for new chart data
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # For AJAX, we only need the activity chart data
        data = get_analytics_data(request.user, period, category)
        return JsonResponse({
            'activity_chart_labels': data['activity_chart_labels'],
            'activity_chart_datasets': data['activity_chart_datasets'],
        })

    # For a normal page load, get all data and render the template
    context = get_analytics_data(request.user, period, category)
    return render(request, 'tracker/analytics.html', context)
    context = get_analytics_data(request.user, period, category)
    return render(request, 'tracker/analytics.html', context)

@login_required
def profile_view(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('tracker:profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    return render(request, 'tracker/profile.html', context)

@login_required
def terminate_account_confirm(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, 'Your account has been successfully terminated.')
        return redirect('tracker:entry_list')
    return render(request, 'tracker/terminate_account_confirm.html')
    # Get the English name of the target language and then translate it.
    target_language_english_name = LANGUAGES.get(target_language, target_language).capitalize()
    try:
        translated_language_name = translator.translate(target_language_english_name, dest=target_language).text
    except (TypeError, AttributeError):
        # If translation of the language name fails, fall back to the English name
        translated_language_name = target_language_english_name

    # Translate static text for the template
    trans_context = {
        't_translated_report': translator.translate('Translated Report', dest=target_language).text,
        't_project': translator.translate('Project', dest=target_language).text,
        't_date_range': translator.translate('Date Range', dest=target_language).text,
        't_language': translator.translate('Language', dest=target_language).text,
        't_all_projects': translator.translate('All Projects', dest=target_language).text,
        't_details': translator.translate('Details', dest=target_language).text,
        't_start_time': translator.translate('Start Time', dest=target_language).text,
        't_end_time': translator.translate('End Time', dest=target_language).text,
        't_duration': translator.translate('Duration', dest=target_language).text,
        't_description': translator.translate('Description', dest=target_language).text,
        't_notes': translator.translate('Notes', dest=target_language).text,
        't_entry': translator.translate('Entry', dest=target_language).text,
        't_no_entries': translator.translate('No entries found for this period.', dest=target_language).text,
    }

    translated_entries = []
    for entry in entries:
        translated_title = translator.translate(entry.title, dest=target_language).text if entry.title else ""
        translated_description = translator.translate(entry.description, dest=target_language).text if entry.description else ""
        translated_notes = translator.translate(entry.notes, dest=target_language).text if entry.notes else ""

        # Pre-format duration for PDF
        duration_str = ""
        if entry.duration:
            total_seconds = int(entry.duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = f'{hours:02}:{minutes:02}:{seconds:02}'

        translated_entries.append({
            'original': entry,
            'title': translated_title,
            'description': translated_description,
            'notes': translated_notes,
            'formatted_duration': duration_str,
        })
    
    project = Project.objects.filter(pk=project_id).first() if project_id else None
    
    context = {
        'entries': translated_entries,
        'start_date': start_date,
        'end_date': end_date,
        'project': project,
        'target_language': translated_language_name,
        'request': request,
        'trans': trans_context,
        'is_rtl': is_rtl,
    }

    if export_format == 'pdf':
        pdf = render_to_pdf('tracker/report_pdf.html', context)
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            filename = f"translated_report_{start_date}_to_{end_date}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="translated_report_{start_date}_to_{end_date}.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Original Title', 'Translated Title', 'Original Description', 'Translated Description',
            'Original Notes', 'Translated Notes', 'Project', 'Start Time', 'Duration (HH:MM:SS)'
        ])
        for item in translated_entries:
            entry = item['original']
            writer.writerow([
                entry.title, item['title'], entry.description, entry['description'],
                entry.notes, item['notes'], entry.project.name if entry.project else '-',
                entry.start_time.strftime('%Y-%m-%d %H:%M:%S'), str(entry.duration)
            ])
        return response

    return render(request, 'tracker/report_translated.html', context)

def daily_earnings_tracker(request):
    # If the essential params are not in the request, redirect with defaults.
    # This handles both initial page load and category changes from the frontend.
    if 'project' not in request.GET or not request.GET.get('project'):
        today = date.today()
        
        # Use category from GET if present (from category dropdown), otherwise default to 'work'
        default_category = request.GET.get('category', 'work')
        
        latest_entry = TimeEntry.objects.filter(
            user=request.user, 
            project__category=default_category, 
            project__isnull=False
        ).order_by('-start_time').first()
        
        default_project_id = latest_entry.project.id if latest_entry else ''

        params = {
            'category': default_category,
            'project': default_project_id,
            'start_date': today.replace(day=1).strftime('%Y-%m-%d'),
            'end_date': today.strftime('%Y-%m-%d'),
        }
        query_string = urlencode({k: v for k, v in params.items() if v})
        return redirect(f"{reverse('tracker:daily_earnings_tracker')}?{query_string}")

    # If we are here, we have GET params (either from defaults or user submission)
    form = ReportForm(request.GET, user=request.user)
    context = {'form': form}

    if form.is_valid():
        project = form.cleaned_data.get('project')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')

        if project and project.hourly_rate and start_date and end_date:
            # --- Swedish Tax Constants ---
            SOCIAL_FEES_RATE = Decimal('0.2897')
            MUNICIPAL_TAX_RATE = Decimal('0.32') # Using a common average

            end_date_inclusive = end_date + timedelta(days=1)
            entries = TimeEntry.objects.filter(
                project=project,
                start_time__gte=start_date,
                end_time__lt=end_date_inclusive,
                user=request.user
            ).order_by('start_time')

            hourly_rate = Decimal(project.hourly_rate)

            # Add worked_duration to each entry for the template
            total_worked_duration = timedelta(0)
            for entry in entries:
                if entry.end_time and entry.start_time:
                    entry.worked_duration = (entry.end_time - entry.start_time) - entry.paused_duration
                    total_worked_duration += entry.worked_duration
                else:
                    entry.worked_duration = timedelta(0)

            # Summary Calculations based on Swedish Sole Trader model
            total_hours = Decimal(total_worked_duration.total_seconds()) / Decimal(3600)
            gross_pay = total_hours * hourly_rate # This is the revenue

            social_fees_amount = gross_pay * SOCIAL_FEES_RATE
            taxable_income = gross_pay - social_fees_amount
            income_tax_amount = taxable_income * MUNICIPAL_TAX_RATE
            net_pay = taxable_income - income_tax_amount

            # Data for chart
            daily_earnings = defaultdict(Decimal)
            for entry in entries:
                date_key = entry.start_time.strftime('%Y-%m-%d')
                worked_hours_entry = Decimal(entry.worked_duration.total_seconds()) / Decimal(3600)
                daily_earnings[date_key] += worked_hours_entry * hourly_rate
            
            chart_labels = sorted(daily_earnings.keys())
            chart_data = [daily_earnings[label] for label in chart_labels]

            context.update({
                'project': project,
                'entries': entries,
                'hourly_rate': hourly_rate,
                'chart_labels': chart_labels,
                'chart_data': chart_data,
                'total_hours': total_hours,
                'gross_pay': gross_pay,
                'social_fees_amount': social_fees_amount,
                'income_tax_amount': income_tax_amount,
                'net_pay': net_pay,
            })

    return render(request, 'tracker/daily_earnings_tracker.html', context)

def income_calculator(request):
    # --- Part 1: Swedish Freelance Rate Calculator ---
    context = {}
    desired_salary_str = request.GET.get('desired_salary')

    if desired_salary_str:
        try:
            # --- Input Data ---
            desired_salary = Decimal(desired_salary_str)
            overhead_costs = Decimal(request.GET.get('overhead_costs', '0'))
            profit_margin_perc = Decimal(request.GET.get('profit_margin', '0'))
            billable_hours = Decimal(request.GET.get('billable_hours', '1')) # Avoid division by zero
            municipal_tax_perc = Decimal(request.GET.get('municipal_tax', '0'))

            # --- Constants for Swedish calculations ---
            SOCIAL_FEES_RATE = Decimal('0.2897')
            VACATION_PAY_RATE = Decimal('0.12')
            PENSION_RATE = Decimal('0.045')
            SICK_LEAVE_BUFFER_RATE = Decimal('0.05')
            STATE_TAX_THRESHOLD = Decimal('598500') # For 2023/2024, annual income
            
            # --- Calculations ---
            social_fees = desired_salary * SOCIAL_FEES_RATE
            vacation_pay = desired_salary * VACATION_PAY_RATE
            pension_savings = desired_salary * PENSION_RATE
            sick_leave_buffer = desired_salary * SICK_LEAVE_BUFFER_RATE

            total_monthly_cost = (desired_salary + social_fees + vacation_pay + 
                                  pension_savings + sick_leave_buffer + overhead_costs)
            
            profit_amount = total_monthly_cost * (profit_margin_perc / 100)
            total_to_invoice = total_monthly_cost + profit_amount
            
            hourly_rate_to_charge = total_to_invoice / billable_hours if billable_hours > 0 else 0

            # Personal take-home pay calculation
            total_tax_amount = desired_salary * (municipal_tax_perc / 100)
            # Note: This is a simplification. Real tax is more complex.
            net_salary = desired_salary - total_tax_amount

            context.update({
                'hourly_rate_to_charge': hourly_rate_to_charge,
                'desired_salary': desired_salary,
                'overhead_costs': overhead_costs,
                'profit_margin': profit_margin_perc,
                'social_fees': social_fees,
                'vacation_pay': vacation_pay,
                'pension_savings': pension_savings,
                'sick_leave_buffer': sick_leave_buffer,
                'total_monthly_cost': total_monthly_cost,
                'profit_amount': profit_amount,
                'total_to_invoice': total_to_invoice,
                'municipal_tax': municipal_tax_perc,
                'total_tax_amount': total_tax_amount,
                'net_salary': net_salary,
                'state_tax_threshold': STATE_TAX_THRESHOLD,
            })
        except (ValueError, TypeError):
            messages.error(request, "Invalid input. Please enter valid numbers.")

    return render(request, 'tracker/income_calculator.html', context)


def ajax_get_project_dates(request):
    project_id = request.GET.get('project_id')
    if project_id:
        project = get_object_or_404(Project, pk=project_id, user=request.user)
        dates = TimeEntry.objects.filter(project=project, user=request.user).aggregate(
            start_date=Min('start_time__date'),
            end_date=Max('end_time__date')
        )
        if dates['start_date'] and dates['end_date']:
            return JsonResponse({
                'success': True,
                'start_date': dates['start_date'].strftime('%Y-%m-%d'),
                'end_date': dates['end_date'].strftime('%Y-%m-%d'),
            })
    return JsonResponse({'success': False})
