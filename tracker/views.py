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
from datetime import timedelta, date
import csv
from django.http import HttpResponse, JsonResponse
from googletrans import Translator, LANGUAGES
from .utils import render_to_pdf
from django.db.models import Min, Max

class HomePageView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        active_entry = TimeEntry.objects.filter(user=request.user, end_time__isnull=True).first()
        projects = Project.objects.filter(user=request.user)
        new_project_id = request.GET.get('project_id')
        new_category = request.GET.get('category')
        context = {
            'active_entry': active_entry,
            'projects': projects,
            'new_project_id': new_project_id,
            'new_category': new_category,
        }
        return render(request, 'home.html', context)

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


@login_required
def add_project_ajax(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        category = request.POST.get('category')
        if name and category:
            project = Project.objects.create(user=request.user, name=name, category=category)
            return JsonResponse({'success': True, 'id': project.id, 'name': project.name})
    return JsonResponse({'success': False, 'error': 'Invalid data'})


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
    translated_entries = []
    for entry in entries:
        # Only translate fields that have content.
        translated_title = translator.translate(entry.title, dest=target_language).text if entry.title else ""
        translated_description = translator.translate(entry.description, dest=target_language).text if entry.description else ""
        translated_notes = translator.translate(entry.notes, dest=target_language).text if entry.notes else ""

        translated_entries.append({
            'original': entry,
            'title': translated_title,
            'description': translated_description,
            'notes': translated_notes,
        })
    
    project = Project.objects.filter(pk=project_id).first() if project_id else None
    
    context = {
        'entries': translated_entries,
        'start_date': start_date,
        'end_date': end_date,
        'project': project,
        'target_language': LANGUAGES.get(target_language, target_language).capitalize(),
        'request': request,
    }

    # If 'export=pdf' is in the URL, generate and return a PDF file
    if export_format == 'pdf':
        pdf = render_to_pdf('tracker/report_pdf.html', context)
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            filename = f"translated_report_{start_date}_to_{end_date}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

    # If 'export=csv' is in the URL, generate and return a CSV file
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
                entry.start_time.strftime('%Y-%m-%d %H:%M:%S'), entry.formatted_duration()
            ])
        return response

    return render(request, 'tracker/report_translated.html', context)


class ReportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Set default dates if not provided: start of month to today
        today = date.today()
        start_of_month = today.replace(day=1)
        initial_data = {
            'start_date': request.GET.get('start_date', start_of_month.strftime('%Y-%m-%d')),
            'end_date': request.GET.get('end_date', today.strftime('%Y-%m-%d')),
            'category': request.GET.get('category', 'work'),
            'project': request.GET.get('project')
        }
        form = ReportForm(initial_data, user=request.user)
        context = {'form': form}

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
                end_time__isnull=False
            ).select_related('project')  # Optimize query

            if project:
                entries = entries.filter(project=project)
            if category:
                entries = entries.filter(category=category)

            # If 'export=csv' is in the URL, generate and return a CSV file
            if export_format == 'csv':
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="time_report_{start_date}_to_{end_date}.csv"'

                writer = csv.writer(response)
                writer.writerow(['Title', 'Project', 'Start Time', 'End Time', 'Duration (HH:MM:SS)', 'Category', 'Description', 'Notes', 'Image URLs'])

                for entry in entries.prefetch_related('images'):
                    image_urls = "; ".join([request.build_absolute_uri(img.image.url) for img in entry.images.all()])
                    writer.writerow([
                        entry.title,
                        entry.project.name if entry.project else '-',
                        entry.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                        entry.end_time.strftime('%Y-%m-%d %H:%M:%S') if entry.end_time else '',
                        entry.formatted_duration(),
                        entry.get_category_display(),
                        entry.description,
                        entry.notes,
                        image_urls,
                    ])
                return response

            total_duration = sum([entry.duration for entry in entries if entry.duration], timedelta())
            total_seconds = int(total_duration.total_seconds())
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

        return render(request, 'tracker/report_form.html', context)


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
        return Project.objects.filter(user=self.request.user).order_by('category', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        projects = self.get_queryset()
        context['work_projects'] = projects.filter(category='work')
        context['personal_projects'] = projects.filter(category='personal')
        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    fields = ['name', 'description', 'category']
    template_name = 'tracker/project_form.html'

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            # Append the new project's ID and category to the redirect URL
            return f"{next_url}?project_id={self.object.pk}&category={self.object.category}"
        return reverse_lazy('tracker:project_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    fields = ['name', 'description', 'category']
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

class TimeEntryDeleteView(LoginRequiredMixin, DeleteView):
    model = TimeEntry
    template_name = 'tracker/timeentry_confirm_delete.html'
    success_url = reverse_lazy('tracker:entry_list')

    def get_queryset(self):
        return TimeEntry.objects.filter(user=self.request.user)
