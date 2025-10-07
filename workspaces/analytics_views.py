from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.urls import reverse
from workspaces.models import TimeEntry, Project
from reports.forms import ReportForm
from django.contrib import messages
from django.db.models import Sum, F, Min, Max
from django.http import JsonResponse
from datetime import timedelta, date, datetime, time
from decimal import Decimal, InvalidOperation
from collections import defaultdict
import csv
from googletrans import Translator, LANGUAGES
from tracker.utils import render_to_pdf
from .mixins import OrganizationPermissionMixin

# --- Report and Translation Views ---

def _get_date_range(period):
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
    
    return start_date, end_date, days_in_period

def _get_base_queryset(user, start_date):
    time_entries_qs = TimeEntry.objects.filter(user=user, end_time__isnull=False)
    if start_date:
        time_entries_qs = time_entries_qs.filter(start_time__gte=start_date)
    
    return time_entries_qs

def _calculate_summary_data(user, start_date):
    summary_qs = TimeEntry.objects.filter(user=user, end_time__isnull=False)
    if start_date:
        summary_qs = summary_qs.filter(start_time__gte=start_date)
        
    work_duration = summary_qs.aggregate(total=Sum(F('end_time') - F('start_time')))['total'] or timedelta()
    personal_duration = timedelta()

    # Calculate total earnings only from projects with an hourly rate > 0
    earnings_entries = summary_qs.filter(project__hourly_rate__gt=0)
    total_earnings = sum(
        (entry.duration.total_seconds() / 3600) * float(entry.project.hourly_rate)
        for entry in earnings_entries
    )

    return work_duration, personal_duration, total_earnings

def _get_context_data(user, start_date, period, time_entries_qs):
    work_duration, personal_duration, total_earnings = _calculate_summary_data(user, start_date)
    summary_qs = TimeEntry.objects.filter(user=user, end_time__isnull=False)
    if start_date:
        summary_qs = summary_qs.filter(start_time__gte=start_date)
    category_chart_labels, category_chart_data = _get_doughnut_chart_data(summary_qs)
    earnings_labels, earnings_data = _get_bar_chart_data(summary_qs)
    activity_labels, activity_datasets = _calculate_activity_by_project(time_entries_qs, start_date, period, user)

    context = {
        'work_duration': work_duration,
        'personal_duration': personal_duration,
        'total_earnings': total_earnings,
        'active_period': period,
        
        'category_chart_labels': category_chart_labels,
        'category_chart_data': category_chart_data,

        'earnings_chart_labels': earnings_labels,
        'earnings_chart_data': earnings_data,

        'activity_chart_labels': activity_labels,
        'activity_chart_datasets': activity_datasets,
    }

    return context

class AnalyticsDashboardView(LoginRequiredMixin, OrganizationPermissionMixin, View):
    def get(self, request, *args, **kwargs):
        user = request.user
        
        # --- Date Range and Category Filtering ---
        period = request.GET.get('period', '30d')
        start_date, end_date, days_in_period = _get_date_range(period)

        # --- Main Queryset ---
        time_entries_qs = self.get_queryset()

        # --- AJAX Request Handling ---
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            activity_labels, activity_datasets = _calculate_activity_by_project(time_entries_qs, start_date, period, user)
            return JsonResponse({
                'activity_chart_labels': activity_labels,
                'activity_chart_datasets': activity_datasets,
            })

        # --- Full Page Load Context ---
        context = _get_context_data(user, start_date, period, time_entries_qs)
        
        return render(request, 'tracker/analytics.html', context)

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
            return render(request, 'tracker/report_form.html', context)

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
                    'tracker/report_untranslated_pdf.html',
                    context,
                    f"report_{start_date}_to_{end_date}.pdf"
                )


            # Use the already calculated total_duration for the HTML view
            context['total_duration'] = total_duration_val
        
        return render(request, 'tracker/report_form.html', context)

class DailyEarningsTrackerView(LoginRequiredMixin, OrganizationPermissionMixin, View):
    def get(self, request, *args, **kwargs):
        form = ReportForm(request.GET or None, user=request.user)
        context = {'form': form}
        project = None

        # Set default values for initial page load
        if not request.GET:
            today = date.today()
            start_of_month = today.replace(day=1)
            
            # Find the most recent project to pre-select
            latest_work_entry = self.get_queryset().filter(
                project__isnull=False
            ).order_by('-start_time').first()
            
            initial_data = {
                'start_date': start_of_month,
                'end_date': today,
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
                project = get_object_or_404(Project, pk=project_id.pk, organization__members=request.user)

            if project and project.hourly_rate and start_date and end_date:
                # --- Swedish Tax Constants ---
                SOCIAL_FEES_RATE = Decimal('0.2897')
                MUNICIPAL_TAX_RATE = Decimal('0.32') # Using a common average

                # Make datetimes timezone-aware to prevent warnings
                start_dt = timezone.make_aware(datetime.combine(start_date, time.min))
                end_dt = timezone.make_aware(datetime.combine(end_date, time.max))

                entries = self.get_queryset().filter(
                    project=project,
                    start_time__gte=start_dt,
                    end_time__lt=end_dt,
                ).order_by('start_time')

                hourly_rate = Decimal(project.hourly_rate)

                total_worked_duration = timedelta(0)
                for entry in entries:
                    duration = (entry.end_time - entry.start_time) - entry.paused_duration
                    entry.worked_duration = max(duration, timedelta(0))
                    total_worked_duration += entry.worked_duration

                # Summary Calculations based on Swedish Sole Trader model
                total_hours = Decimal(total_worked_duration.total_seconds()) / Decimal(3600)
                # Round to 2 decimal places for currency
                gross_pay = (total_hours * hourly_rate).quantize(Decimal('0.01'))

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

class IncomeCalculatorView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
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
            except (InvalidOperation, TypeError):
                # Handle cases where conversion to Decimal fails or inputs are not numbers
                pass
        return render(request, 'tracker/income_calculator.html', context)

class TranslateReportView(LoginRequiredMixin, OrganizationPermissionMixin, View):
    def get(self, request, *args, **kwargs):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        project_id = request.GET.get('project')
        target_language = request.GET.get('target_language')
        export_format = request.GET.get('export')

        if not all([start_date, end_date, target_language]):
            return redirect('workspaces:analytics:reports')

        entries = self.get_queryset().filter(
            start_time__date__gte=start_date,
            end_time__date__lte=end_date,
            end_time__isnull=False
        ).select_related('project')

        if project_id:
            entries = entries.filter(project_id=project_id)

        translator = Translator()
        trans_context = _get_translation_context()
        translated_entries = _get_translated_entries(entries)

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

        return render(request, 'tracker/report_translated.html', context)

class IncomeCalculatorView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
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
            except (InvalidOperation, TypeError):
                # Handle cases where conversion to Decimal fails or inputs are not numbers
                pass
        return render(request, 'tracker/income_calculator.html', context)
