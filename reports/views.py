from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.urls import reverse
from workspaces.models import TimeEntry, Project
from .forms import ReportForm
from django.contrib import messages
from django.db.models import Sum, F, Min, Max
from django.http import JsonResponse
from datetime import timedelta, date, datetime, time
from decimal import Decimal, InvalidOperation
from collections import defaultdict
import csv
from googletrans import Translator, LANGUAGES
from .utils import render_to_pdf
from workspaces.mixins import OrganizationPermissionMixin

class ReportView(LoginRequiredMixin, OrganizationPermissionMixin, View):
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
            return render(request, 'reports/report_form.html', context)

        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            project = form.cleaned_data.get('project')
            export_format = request.GET.get('export')

            entries = self.get_queryset().filter(
                start_time__date__gte=start_date,
                end_time__date__lte=end_date,
                end_time__isnull=False,
                is_archived=False
            ).select_related('project')

            if project:
                entries = entries.filter(project=project)

            # Pre-format durations for the PDF context
            for entry in entries:
                if entry.duration:
                    total_seconds = int(entry.duration.total_seconds())
                    hours, remainder = divmod(total_seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    entry.formatted_duration = f'{hours:02}:{minutes:02}:{seconds:02}'

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
                writer.writerow(['Title', 'Project', 'Start Time', 'End Time', 'Duration (HH:MM:SS)', 'Description', 'Notes'])
                for entry in entries:
                    writer.writerow([
                        entry.title,
                        entry.project.name if entry.project else '-',
                        entry.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                        entry.end_time.strftime('%Y-%m-%d %H:%M:%S') if entry.end_time else '',
                        str(entry.duration),
                        entry.description,
                        entry.notes,
                    ])
                return response
            
            if export_format == 'pdf':
                return _generate_pdf_response(
                    'reports/report_untranslated_pdf.html',
                    context,
                    f"report_{start_date}_to_{end_date}.pdf"
                )


            # Use the already calculated total_duration for the HTML view
            context['total_duration'] = total_duration_val
        
        return render(request, 'reports/report_form.html', context)

@login_required
def _get_translation_context(translator, target_language):
    """Translates UI elements and returns a context dictionary."""
    # Helper to safely translate text, falling back to original on error
    def translate_safely(text, default_text=None):
        if not text:
            return default_text if default_text is not None else ""
        try:
            return translator.translate(text, dest=target_language).text
        except (TypeError, AttributeError):
            return default_text if default_text is not None else text

    return {
        't_translated_report': translate_safely('Translated Report'),
        't_project': translate_safely('Project'),
        't_date_range': translate_safely('Date Range'),
        't_language': translate_safely('Language'),
        't_all_projects': translate_safely('All Projects'),
        't_details': translate_safely('Details'),
        't_start_time': translate_safely('Start Time'),
        't_end_time': translate_safely('End Time'),
        't_duration': translate_safely('Duration'),
        't_description': translate_safely('Description'),
        't_notes': translate_safely('Notes'),
        't_entry': translate_safely('Entry'),
        't_no_entries': translate_safely('No entries found for this period.'),
    }

@login_required
def _get_translated_entries(entries, translator, target_language):
    """Translates time entry data and returns a list of dictionaries."""
    translated_entries = []
    for entry in entries:
        duration_str = ""
        if entry.duration:
            total_seconds = int(entry.duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = f'{hours:02}:{minutes:02}:{seconds:02}'

        translated_entries.append({
            'original': entry,
            'title': translate_safely(entry.title, translator, target_language),
            'description': translate_safely(entry.description, translator, target_language),
            'notes': translate_safely(entry.notes, translator, target_language),
            'formatted_duration': duration_str,
        })
    return translated_entries

@login_required
def _generate_translated_pdf_response(context, start_date, end_date):
    """Generates a PDF response for a translated report."""
    pdf_context = context.copy()
    pdf_context.update(context['trans'])
    pdf = render_to_pdf('reports/report_pdf.html', pdf_context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"translated_report_{start_date}_to_{end_date}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    return None

@login_required
def _generate_translated_csv_response(translated_entries, start_date, end_date):
    """Generates a CSV response for a translated report."""
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

class TranslateReportView(LoginRequiredMixin, OrganizationPermissionMixin, View):
    def get(self, request, *args, **kwargs):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        project_id = request.GET.get('project')
        target_language = request.GET.get('target_language')
        export_format = request.GET.get('export')

        if not all([start_date, end_date, target_language]):
            return redirect('reports:reports')

        entries = self.get_queryset().filter(
            start_time__date__gte=start_date,
            end_time__date__lte=end_date,
            end_time__isnull=False
        ).select_related('project')

        if project_id:
            entries = entries.filter(project_id=project_id)

        translator = Translator()
        trans_context = _get_translation_context(translator, target_language)
        translated_entries = _get_translated_entries(entries, translator, target_language)

        # --- RTL Language Check ---
        RTL_LANGUAGES = ['ar', 'he', 'fa', 'ur']
        is_rtl = target_language in RTL_LANGUAGES

        # Get the English name of the target language and then translate it.
        target_language_english_name = LANGUAGES.get(target_language, target_language).capitalize()
        try:
            translated_language_name = translator.translate(target_language_english_name, dest=target_language).text
        except (TypeError, AttributeError):
            translated_language_name = target_language_english_name

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
            return _generate_translated_pdf_response(context, start_date, end_date)

        if export_format == 'csv':
            return _generate_translated_csv_response(translated_entries, start_date, end_date)

        return render(request, 'reports/report_translated.html', context)