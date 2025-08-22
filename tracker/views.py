from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from django.urls import reverse_lazy
from .models import TimeEntry, Project
from .forms import TimeEntryForm, ProjectForm, TimeEntryFilterForm, ReportForm, TimeEntryUpdateForm
from django.contrib import messages
from django.db.models import Sum, F, Min, Max
from datetime import timedelta, date
import csv
from django.http import HttpResponse, JsonResponse
from urllib.parse import urlencode
from googletrans import Translator, LANGUAGES
from .utils import render_to_pdf

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
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().filter(user=self.request.user)
        self.filter_form = TimeEntryFilterForm(self.request.GET)

        # Annotate with duration for sorting
        queryset = queryset.annotate(duration_calc=F('end_time') - F('start_time'))

        project_id = self.request.GET.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        if self.filter_form.is_valid():
            start_date = self.filter_form.cleaned_data.get('start_date')
            if start_date:
                queryset = queryset.filter(start_time__date__gte=start_date)

            end_date = self.filter_form.cleaned_data.get('end_date')
            if end_date:
                queryset = queryset.filter(end_time__date__lte=end_date)

            category = self.filter_form.cleaned_data.get('category')
            if category:
                queryset = queryset.filter(category=category)
            
            if self.filter_form.cleaned_data.get('show_archived'):
                queryset = queryset.filter(is_archived=True)
            else:
                queryset = queryset.filter(is_archived=False)
        else:
            queryset = queryset.filter(is_archived=False)

        # Sorting logic
        sort_by = self.request.GET.get('sort_by', 'start_time') # Default sort
        sort_dir = self.request.GET.get('sort_dir', 'desc')
        
        valid_sort_fields = ['title', 'project__name', 'start_time', 'end_time', 'duration', 'category', 'paused_duration']
        
        # Map the 'duration' sort field to our calculated field
        sort_field_db = 'duration_calc' if sort_by == 'duration' else sort_by

        if sort_by in valid_sort_fields:
            if sort_dir == 'desc':
                sort_field_db = f'-{sort_field_db}'
            queryset = queryset.order_by(sort_field_db)
        else:
            queryset = queryset.order_by('-start_time')


        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Prepare data for the template
        filter_data = self.filter_form.cleaned_data if self.filter_form.is_valid() else {}
        selected_project_id = self.request.GET.get('project')
        if selected_project_id:
            filter_data['project'] = selected_project_id
        context['filter_form'] = filter_data

        # Pass sorting info to template
        context['sort_by'] = self.request.GET.get('sort_by', 'start_time')
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
    form_class = TimeEntryForm
    template_name = 'tracker/timeentry_form.html'
    success_url = reverse_lazy('tracker:entry_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class TimeEntryUpdateView(LoginRequiredMixin, UpdateView):
    model = TimeEntry
    form_class = TimeEntryUpdateForm
    template_name = 'tracker/timeentry_form.html'
    success_url = reverse_lazy('tracker:entry_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

class TimeEntryDeleteView(LoginRequiredMixin, DeleteView):
    model = TimeEntry
    template_name = 'tracker/timeentry_confirm_delete_single.html'
    success_url = reverse_lazy('tracker:entry_list')

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

# --- Bulk Action Views ---

@login_required
def time_entry_bulk_delete_confirm(request):
    selected_ids = request.GET.getlist('selected_entries')
    entries_to_delete = TimeEntry.objects.filter(user=request.user, pk__in=selected_ids)
    context = {
        'entries_to_delete': entries_to_delete
    }
    return render(request, 'tracker/timeentry_confirm_delete.html', context)

@login_required
def time_entry_bulk_delete(request):
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_entries')
        if selected_ids:
            TimeEntry.objects.filter(user=request.user, pk__in=selected_ids).delete()
            messages.success(request, 'Selected time entries have been deleted.')
    return redirect('tracker:entry_list')

@login_required
def time_entry_bulk_archive_confirm(request):
    selected_ids = request.GET.getlist('selected_entries')
    entries_to_process = TimeEntry.objects.filter(user=request.user, pk__in=selected_ids)
    context = {
        'entries_to_process': entries_to_process,
        'action': 'archive'
    }
    return render(request, 'tracker/timeentry_confirm_archive.html', context)

@login_required
def time_entry_bulk_unarchive_confirm(request):
    selected_ids = request.GET.getlist('selected_entries')
    entries_to_process = TimeEntry.objects.filter(user=request.user, pk__in=selected_ids)
    context = {
        'entries_to_process': entries_to_process
    }
    return render(request, 'tracker/timeentry_confirm_unarchive.html', context)

@login_required
def time_entry_bulk_archive(request):
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_entries')
        action = request.POST.get('action')
        if selected_ids and action in ['archive', 'unarchive']:
            is_archived_status = (action == 'archive')
            updated_count = TimeEntry.objects.filter(user=request.user, pk__in=selected_ids).update(is_archived=is_archived_status)
            messages.success(request, f'{updated_count} selected entries have been {action}d.')
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
        
        total_duration = TimeEntry.objects.filter(user=user, end_time__isnull=False).aggregate(
            total=Sum(F('end_time') - F('start_time'))
        )['total'] or timedelta()

        time_per_project = TimeEntry.objects.filter(user=user, end_time__isnull=False) \
            .values('project__name') \
            .annotate(total_duration=Sum(F('end_time') - F('start_time'))) \
            .order_by('-total_duration')

        time_per_category = TimeEntry.objects.filter(user=user, end_time__isnull=False) \
            .values('category') \
            .annotate(total_duration=Sum(F('end_time') - F('start_time'))) \
            .order_by('-total_duration')

        context = {
            'total_time_tracked': total_duration,
            'time_per_project': time_per_project,
            'time_per_category': time_per_category,
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
                entry.title, item['title'], entry.description, item['description'],
                entry.notes, item['notes'], entry.project.name if entry.project else '-',
                entry.start_time.strftime('%Y-%m-%d %H:%M:%S'), str(entry.duration)
            ])
        return response

    return render(request, 'tracker/report_translated.html', context)
