from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from .models import Project, TimeEntry, Profile, TimeEntryImage
from django.utils import timezone
from PIL import Image
from django.core.files import File
import os
from django.http import QueryDict, HttpResponse
from urllib.parse import urlencode
from django.template import Context, Template
from datetime import timedelta
from unittest.mock import patch, MagicMock
from decimal import Decimal, InvalidOperation
from .utils import format_duration_hms, render_to_pdf
from .forms import TimeEntryManualForm

class ProjectListViewTest(TestCase):
    def setUp(self):
        # Create a test user that we can log in with
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpassword'
        )
        # Create a test project associated with the user
        self.project = Project.objects.create(
            name='Test Work Project',
            description='A test project for work.',
            category='work',
            user=self.user
        )

    def test_project_list_view_requires_login(self):
        """
        Test that the project list page redirects if the user is not logged in.
        """
        # The URL name 'tracker:project_list' is based on your template paths.
        # If your URL is named differently, you may need to adjust this.
        url = reverse('tracker:project_list')
        response = self.client.get(url)

        # Check that the user is redirected (status code 302) to the login page.
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'/accounts/login/?next={url}')

    def test_project_list_view_loads_for_logged_in_user(self):
        """
        Test that the project list page loads correctly for a logged-in user.
        """
        # Log the test user in
        self.client.login(username='testuser', password='testpassword')

        url = reverse('tracker:project_list')
        response = self.client.get(url)

        # Check that the page loads successfully (status code 200).
        self.assertEqual(response.status_code, 200)
        # Check that the correct template is used.
        self.assertTemplateUsed(response, 'tracker/project_list.html')

    def test_project_is_displayed_on_list_page(self):
        """
        Test that a created project's name is visible on the project list page.
        """
        self.client.login(username='testuser', password='testpassword')
        url = reverse('tracker:project_list')
        response = self.client.get(url)

        # Check that the response contains the name of our test project.
        self.assertContains(response, self.project.name)


class ProjectCreateViewTest(TestCase):
    def setUp(self):
        # Create a test user
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpassword'
        )
        # Log the user in for all tests in this class
        self.client.login(username='testuser', password='testpassword')
        self.url = reverse('tracker:project_create')

    def test_create_project_page_loads(self):
        """Test that the project creation page loads correctly."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/project_form.html')

    def test_create_project_successfully(self):
        """Test that a new project can be created via a POST request."""
        form_data = {
            'name': 'New Test Project',
            'description': 'A brand new project for testing.',
            'category': 'personal',
            'hourly_rate': 100.00,  # Add the missing hourly_rate field
        }
        response = self.client.post(self.url, data=form_data)

        # Check that we are redirected to the project list page after creation
        self.assertRedirects(response, reverse('tracker:project_list'))

        # Check that the project was actually created in the database
        self.assertTrue(Project.objects.filter(name='New Test Project').exists())

        # Check that the project is associated with the correct user
        new_project = Project.objects.get(name='New Test Project')
        self.assertEqual(new_project.user, self.user)

    def test_delete_project_view(self):
        """Test that a project can be deleted."""
        project_to_delete = Project.objects.create(
            user=self.user, name='Will be deleted'
        )
        delete_url = reverse('tracker:project_delete', kwargs={'pk': project_to_delete.pk})
        self.assertTrue(Project.objects.filter(pk=project_to_delete.pk).exists())
        response = self.client.post(delete_url)
        self.assertRedirects(response, reverse('tracker:project_list'))
        self.assertFalse(Project.objects.filter(pk=project_to_delete.pk).exists())

    def test_delete_project_get_confirm_page(self):
        """Test that the project delete confirmation page loads."""
        project_to_delete = Project.objects.create(user=self.user, name='Confirm Delete')
        delete_url = reverse('tracker:project_delete', kwargs={'pk': project_to_delete.pk})
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/project_confirm_delete.html')

    def test_create_project_with_next_url(self):
        """Test that creating a project with a 'next' param redirects correctly."""
        next_url = reverse('tracker:home')
        url_with_next = f"{self.url}?next={next_url}"
        form_data = {
            'name': 'Next URL Project',
            'description': 'Testing the next param.',
            'category': 'work',
            'hourly_rate': 50.00,
        }
        response = self.client.post(url_with_next, data=form_data)
        
        new_project = Project.objects.get(name='Next URL Project')
        expected_params = urlencode({
            'new_project_id': new_project.pk,
            'new_category': new_project.category
        })
        self.assertRedirects(response, f"{next_url}?{expected_params}")

class TimerViewsTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.client.login(username='testuser', password='testpassword')
        self.project = Project.objects.create(
            name='Test Project',
            user=self.user
        )
        self.start_url = reverse('tracker:start_timer')
        self.stop_url = reverse('tracker:stop_timer')
        self.pause_url = reverse('tracker:pause_timer')
        self.resume_url = reverse('tracker:resume_timer')

    def test_start_timer_with_project(self):
        response = self.client.post(self.start_url, {'project': self.project.id, 'title': 'Test Title'})
        self.assertRedirects(response, reverse('tracker:home'))
        self.assertTrue(TimeEntry.objects.filter(user=self.user, end_time__isnull=True, project=self.project).exists())

    def test_start_timer_without_project(self):
        response = self.client.post(self.start_url, {'title': 'Test Title'})
        self.assertRedirects(response, reverse('tracker:home'))
        self.assertTrue(TimeEntry.objects.filter(user=self.user, end_time__isnull=True, project__isnull=True).exists())

    def test_start_timer_with_invalid_project(self):
        response = self.client.post(self.start_url, {'project': 999, 'title': 'Invalid Project Test'})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(TimeEntry.objects.filter(title='Invalid Project Test').exists())

    def test_stop_timer_get_request(self):
        response = self.client.get(self.stop_url)
        self.assertRedirects(response, reverse('tracker:home'))

    def test_start_timer_get_request(self):
        response = self.client.get(self.start_url)
        self.assertRedirects(response, reverse('tracker:home'))
        self.assertFalse(TimeEntry.objects.filter(user=self.user, end_time__isnull=True).exists())

    def test_start_timer_already_running(self):
        TimeEntry.objects.create(user=self.user, title='Test Title', start_time=timezone.now())
        response = self.client.post(self.start_url, {'title': 'Another Title'})
        self.assertRedirects(response, reverse('tracker:home'))
        self.assertEqual(TimeEntry.objects.filter(user=self.user, end_time__isnull=True).count(), 1)

    def test_stop_timer_running(self):
        entry = TimeEntry.objects.create(user=self.user, title='Test Title', project=self.project, start_time=timezone.now())
        response = self.client.post(self.stop_url)
        self.assertRedirects(response, reverse('tracker:entry_update', kwargs={'pk': entry.pk}))
        self.assertFalse(TimeEntry.objects.filter(user=self.user, end_time__isnull=True).exists())

    def test_stop_timer_not_running(self):
        response = self.client.post(self.stop_url)
        self.assertRedirects(response, reverse('tracker:home'))
        self.assertFalse(TimeEntry.objects.filter(user=self.user, end_time__isnull=True).exists())

    def test_pause_timer_running(self):
        TimeEntry.objects.create(user=self.user, title='Test Title', project=self.project, start_time=timezone.now())
        response = self.client.post(self.pause_url)
        self.assertRedirects(response, reverse('tracker:home'))
        self.assertTrue(TimeEntry.objects.filter(user=self.user, is_paused=True).exists())

    def test_pause_timer_not_running(self):
        response = self.client.post(self.pause_url)
        self.assertRedirects(response, reverse('tracker:home'))
        self.assertFalse(TimeEntry.objects.filter(user=self.user, is_paused=True).exists())

    def test_resume_timer_paused(self):
        entry = TimeEntry.objects.create(user=self.user, title='Test Title', project=self.project, start_time=timezone.now(), is_paused=True, last_pause_time=timezone.now())
        response = self.client.post(self.resume_url)
        self.assertRedirects(response, reverse('tracker:home'))
        entry.refresh_from_db()
        self.assertFalse(entry.is_paused)

    def test_resume_timer_not_paused(self):
        TimeEntry.objects.create(user=self.user, title='Test Title', project=self.project, start_time=timezone.now())
        response = self.client.post(self.resume_url)
        self.assertRedirects(response, reverse('tracker:home'))
        self.assertFalse(TimeEntry.objects.filter(user=self.user, is_paused=True).exists())

    def test_stop_timer_while_paused(self):
        start_time = timezone.now() - timedelta(minutes=10)
        pause_time = timezone.now() - timedelta(minutes=5)
        entry = TimeEntry.objects.create(
            user=self.user,
            title='Paused Stop Test',
            start_time=start_time,
            is_paused=True,
            last_pause_time=pause_time
        )
        response = self.client.post(self.stop_url)
        self.assertRedirects(response, reverse('tracker:entry_update', kwargs={'pk': entry.pk}))
        entry.refresh_from_db()
        self.assertIsNotNone(entry.end_time)
        self.assertFalse(entry.is_paused)
        self.assertIsNone(entry.last_pause_time)
        self.assertGreater(entry.paused_duration, timedelta(seconds=290)) # Should be ~5 minutes (300s)

class TimeEntryUpdateViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.client.login(username='testuser', password='testpassword')
        self.project = Project.objects.create(
            name='Test Project',
            user=self.user,
            category='work'
        )
        self.entry = TimeEntry.objects.create(
            user=self.user,
            project=self.project,
            title='Test Entry',
            category='work',
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now()
        )
        self.url = reverse('tracker:entry_update', kwargs={'pk': self.entry.pk})

    def test_update_view_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/timeentry_update_form.html')

    def test_update_entry_successfully(self):
        form_data = {
            'title': 'Updated Title',
            'project': self.project.id,
            'category': 'work',
            'start_time': self.entry.start_time.strftime('%Y-%m-%dT%H:%M'),
            'end_time': self.entry.end_time.strftime('%Y-%m-%dT%H:%M'),
        }
        response = self.client.post(self.url, data=form_data)
        self.assertRedirects(response, reverse('tracker:entry_list'))
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.title, 'Updated Title')

    def test_update_entry_with_edited_time(self):
        form_data = {
            'title': 'Updated Title',
            'project': self.project.id,
            'category': 'work',
            'start_time': self.entry.start_time.strftime('%Y-%m-%dT%H:%M'),
            'end_time': self.entry.end_time.strftime('%Y-%m-%dT%H:%M'),
            'time_details_edited_flag': 'true',
        }
        response = self.client.post(self.url, data=form_data)
        self.assertRedirects(response, reverse('tracker:entry_list'))
        self.entry.refresh_from_db()
        self.assertTrue(self.entry.was_edited)

    def test_update_entry_with_image(self):
        # Create a dummy image file
        image = Image.new('RGB', (100, 100), color = 'red')
        image_path = 'test_image.png'
        image.save(image_path)

        with open(image_path, 'rb') as f:
            form_data = {
                'title': 'Updated Title',
                'start_time': self.entry.start_time.strftime('%Y-%m-%dT%H:%M'),
                'end_time': self.entry.end_time.strftime('%Y-%m-%dT%H:%M'),
                # Add all required fields for the form to be valid
                'project': self.project.id,
                'category': 'work',
                'description': 'Test description.',
                'pause_hours': 0,
                'pause_minutes': 10,
                'pause_seconds': 0,
            }
            response = self.client.post(self.url, data={**form_data, 'images': f})

        self.assertRedirects(response, reverse('tracker:entry_list'))
        self.assertEqual(self.entry.images.count(), 1)

        # Clean up the test image
        os.remove(image_path)

class TimeEntryCreateViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.url = reverse('tracker:entry_create')

    def test_create_entry_with_image(self):
        image = Image.new('RGB', (100, 100), color='green')
        image_path = 'test_create_image.png'
        image.save(image_path)

        with open(image_path, 'rb') as f:
            form_data = {
                'title': 'Create With Image',
                'category': 'work',
                'start_time': timezone.now().strftime('%Y-%m-%dT%H:%M'),
                'end_time': (timezone.now() + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),
            }
            response = self.client.post(self.url, data={**form_data, 'images': f})

        self.assertRedirects(response, reverse('tracker:entry_list'))
        entry = TimeEntry.objects.get(title='Create With Image')
        self.assertEqual(entry.images.count(), 1)
        os.remove(image_path)

class TimeEntryDeleteViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.entry = TimeEntry.objects.create(
            user=self.user,
            title='Entry to Delete',
            start_time=timezone.now()
        )
        self.url = reverse('tracker:entry_delete', kwargs={'pk': self.entry.pk})

    def test_delete_view_get_request(self):
        """Test that a GET request to the delete view shows the confirmation page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/timeentry_confirm_delete.html')
        self.assertContains(response, 'Are you sure you want to delete')

    def test_delete_view_post_request(self):
        """Test that a POST request deletes the entry."""
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('tracker:entry_list'))
        self.assertFalse(TimeEntry.objects.filter(pk=self.entry.pk).exists())

class TimeEntryListViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.client.login(username='testuser', password='testpassword')
        self.project = Project.objects.create(
            name='Test Project',
            user=self.user,
            category='work'
        )
        self.entry1 = TimeEntry.objects.create(
            user=self.user,
            project=self.project,
            title='Test Entry 1',
            category='work',
            start_time=timezone.now() - timezone.timedelta(days=2),
            end_time=timezone.now() - timezone.timedelta(days=2)
        )
        self.entry2 = TimeEntry.objects.create(
            user=self.user,
            project=self.project,
            title='Test Entry 2',
            category='personal',
            start_time=timezone.now() - timezone.timedelta(days=1),
            end_time=timezone.now() - timezone.timedelta(days=1),
            is_archived=True
        )
        self.url = reverse('tracker:entry_list')

    def test_list_view_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/timeentry_list.html')

    def test_filter_by_date(self):
        response = self.client.get(self.url, {
            'start_date': (timezone.now() - timezone.timedelta(days=2)).strftime('%Y-%m-%d'),
            'end_date': (timezone.now() - timezone.timedelta(days=2)).strftime('%Y-%m-%d')
        })
        self.assertContains(response, 'Test Entry 1')
        self.assertNotContains(response, 'Test Entry 2')

    def test_filter_by_category(self):
        response = self.client.get(self.url, {'category': 'work'})
        self.assertContains(response, 'Test Entry 1')
        self.assertNotContains(response, 'Test Entry 2')

    def test_filter_by_project(self):
        response = self.client.get(self.url, {'project': self.project.id})
        self.assertContains(response, 'Test Entry 1')
        self.assertNotContains(response, 'Test Entry 2')

    def test_show_archived(self):
        response = self.client.get(self.url, {'show_archived': 'on'})
        self.assertContains(response, 'Test Entry 2')

    def test_sort_by_title(self):
        response = self.client.get(self.url, {'sort_by': 'task', 'sort_dir': 'asc'})
        self.assertContains(response, 'Test Entry 1')

    def test_sorting_by_multiple_fields(self):
        # Test sorting by project name
        response = self.client.get(self.url, {'sort_by': 'project', 'sort_dir': 'asc'})
        self.assertEqual(response.status_code, 200)
        # Test sorting by duration
        response = self.client.get(self.url, {'sort_by': 'duration', 'sort_dir': 'desc'})
        self.assertEqual(response.status_code, 200)

    def test_pagination_disabled_with_filters(self):
        # Create more entries than paginate_by
        for i in range(20):
            TimeEntry.objects.create(
                user=self.user,
                title=f'Entry for pagination test {i}',
                start_time=timezone.now(),
                end_time=timezone.now()
            )
        # Request with a filter
        response = self.client.get(self.url, {'category': 'work'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['is_paginated'])

    def test_list_view_with_invalid_form_data(self):
        # Send an invalid date format
        response = self.client.get(self.url, {'start_date': 'not-a-date'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.entry1, response.context['entries'])
        self.assertNotIn(self.entry2, response.context['entries'])

class TemplateTagsTest(TestCase):
    def test_human_duration_filter(self):
        tpl = Template('{% load tracker_tags %}{{ duration|human_duration }}')
        
        # Test with hours, minutes, and seconds
        duration = timedelta(seconds=3661) # 1h 1m 1s
        rendered = tpl.render(Context({'duration': duration}))
        self.assertEqual(rendered, '1h 1m 1s')

        # Test with only minutes and seconds
        duration = timedelta(seconds=150) # 2m 30s
        rendered = tpl.render(Context({'duration': duration}))
        self.assertEqual(rendered, '2m 30s')

        # Test with only seconds
        duration = timedelta(seconds=45) # 45s
        rendered = tpl.render(Context({'duration': duration}))
        self.assertEqual(rendered, '45s')

        # Test with zero duration
        duration = timedelta(seconds=0)
        rendered = tpl.render(Context({'duration': duration}))
        self.assertEqual(rendered, '0s')

        # Test with negative duration
        duration = timedelta(seconds=-10)
        rendered = tpl.render(Context({'duration': duration}))
        self.assertEqual(rendered, '0s')

        # Test with non-timedelta input
        rendered = tpl.render(Context({'duration': 123}))
        self.assertEqual(rendered, '')

    def test_url_replace_tag(self):
        # Mock a request object with a GET query string
        class MockRequest:
            def __init__(self, query_string=''):
                self.GET = QueryDict(query_string)

        context = Context({'request': MockRequest('page=1&sort=name')})
        # Test adding a new parameter
        tpl = Template('{% load tracker_tags %}{% url_replace new_param="test" %}')
        rendered = tpl.render(context)
        self.assertIn('page=1', rendered)
        self.assertIn('sort=name', rendered)
        self.assertIn('new_param=test', rendered)
 
        # Test replacing an existing parameter
        tpl = Template('{% load tracker_tags %}{% url_replace page=2 %}')
        rendered = tpl.render(context)
        self.assertIn('page=2', rendered)
        self.assertIn('sort=name', rendered)
        self.assertNotIn('page=1', rendered)
 
    def test_sort_url_tag(self):
        # Mock a request object
        class MockRequest:
            def __init__(self, get_params_str):
                self.GET = QueryDict(get_params_str)
        
        # Test initial sort on a field
        context = Context({'request': MockRequest('')})
        tpl = Template("{% load tracker_tags %}{% sort_url 'title' %}")
        rendered = tpl.render(context)
        self.assertEqual(rendered, 'sort_by=title&amp;sort_dir=asc')

        # Test toggling from asc to desc
        context = Context({'request': MockRequest('sort_by=title&sort_dir=asc')})
        rendered = tpl.render(context)
        self.assertEqual(rendered, 'sort_by=title&amp;sort_dir=desc')

    def test_calculate_entry_price_tag(self):
        class MockEntry:
            def __init__(self, duration_seconds):
                self.worked_duration = timedelta(seconds=duration_seconds)

        # Test with valid duration and rate
        entry = MockEntry(3600) # 1 hour
        hourly_rate = Decimal('50.00')
        tpl = Template('{% load tracker_tags %}{% calculate_entry_price entry hourly_rate %}')
        rendered = tpl.render(Context({'entry': entry, 'hourly_rate': hourly_rate}))
        self.assertEqual(rendered, "50.00")

        # Test with no rate
        entry = MockEntry(3600)
        rendered = tpl.render(Context({'entry': entry, 'hourly_rate': None}))
        self.assertEqual(rendered, "0.00")

class UtilsTest(TestCase):
    def test_format_duration_hms(self):
        self.assertEqual(format_duration_hms(timedelta(seconds=5)), "5s")
        self.assertEqual(format_duration_hms(timedelta(seconds=65)), "1m 5s")
        self.assertEqual(format_duration_hms(timedelta(seconds=3665)), "1h 1m 5s")
        self.assertEqual(format_duration_hms(timedelta(hours=2, minutes=30)), "2h 30m")
        self.assertEqual(format_duration_hms(timedelta(0)), "0s")
        self.assertEqual(format_duration_hms(None), "0s")
        self.assertEqual(format_duration_hms(timedelta(seconds=-10)), "0s")

    @patch('tracker.utils.pisa.pisaDocument')
    def test_render_to_pdf_error(self, mock_pisa):
        # Simulate a PDF generation error
        mock_pisa.return_value.err = 1
        # The 'report_pdf.html' template is for translated reports and requires
        # specific context variables. Provide a minimal context to allow it to render.
        trans_dict = {
            't_translated_report': '', 't_project': '', 't_date_range': '',
            't_language': '', 't_all_projects': '', 't_details': '',
            't_start_time': '', 't_end_time': '', 't_duration': '',
            't_description': '', 't_notes': '', 't_entry': '', 't_no_entries': ''
        }
        context = {
            'trans': trans_dict,
            'entries': [],
            'project': None,
            'start_date': '2023-01-01',
            'end_date': '2023-01-31',
            'target_language': 'Test Language',
            'request': MagicMock(),
            'is_rtl': False,
        }
        # The view unpacks the translated strings to the top level for PDFs.
        context.update(trans_dict)
        pdf = render_to_pdf('tracker/report_pdf.html', context)
        self.assertIsNone(pdf)

class ProfileViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpassword',
            first_name='Test',
            last_name='User',
            email='test@example.com'
        )
        # Profile is created automatically by signal
        self.profile = self.user.profile
        self.profile.country = 'SE'
        self.profile.save()
        
        self.client.login(username='testuser', password='testpassword')
        self.url = reverse('tracker:profile')

    def test_profile_view_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/profile.html')
        self.assertContains(response, 'test@example.com')
        self.assertContains(response, 'Sweden') # From country code 'SE'

    def test_profile_view_with_job_title(self):
        # Set a job title and test that it's displayed
        self.profile.job_title = 'Senior Developer'
        self.profile.save()
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Senior Developer')
        self.assertContains(response, 'Job Title')

    def test_profile_view_post_success(self):
        form_data = {
            'first_name': 'UpdatedFirst',
            'last_name': 'UpdatedLast',
            'email': 'updated@example.com',
            'job_title': 'Software Engineer',
            'country': 'US',
            'address': '123 Main St',
            'phone_number': '555-1234'
        }
        response = self.client.post(self.url, data=form_data)
        self.assertRedirects(response, self.url)
        
        self.user.refresh_from_db()
        self.profile.refresh_from_db()

        self.assertEqual(self.user.first_name, 'UpdatedFirst')
        self.assertEqual(self.user.last_name, 'UpdatedLast')
        self.assertEqual(self.user.email, 'updated@example.com')
        self.assertEqual(self.profile.job_title, 'Software Engineer')
        self.assertEqual(str(self.profile.country), 'US')
        self.assertEqual(self.profile.address, '123 Main St')
        self.assertEqual(self.profile.phone_number, '555-1234')

    def test_profile_view_post_invalid(self):
        form_data = {
            'first_name': 'UpdatedFirst',
            'last_name': 'UpdatedLast',
            'email': 'not-an-email', # Invalid email
            'country': 'US',
        }
        response = self.client.post(self.url, data=form_data)
        self.assertEqual(response.status_code, 200) # Should re-render the form
        self.assertContains(response, 'Enter a valid email address.')

        # Check that data was not saved
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'test@example.com')

class AjaxViewsTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.client.login(username='testuser', password='testpassword')
        self.project = Project.objects.create(
            name='Test Project',
            user=self.user,
            category='work'
        )
        self.entry = TimeEntry.objects.create(
            user=self.user,
            project=self.project,
            title='AJAX Test Entry',
            start_time=timezone.now() - timedelta(hours=2),
            end_time=timezone.now() - timedelta(hours=1),
            paused_duration=timedelta(minutes=15),
            description='A description.',
            notes='Some notes.'
        )
        # Create a dummy image for the entry
        image = Image.new('RGB', (100, 100), color='blue')
        image_path = 'test_ajax_image.png'
        image.save(image_path)
        with open(image_path, 'rb') as f:
            self.image = TimeEntryImage.objects.create(time_entry=self.entry, image=File(f, name='test_ajax_image.png'))
        os.remove(image_path)

    def test_get_time_entry_details_success(self):
        url = reverse('tracker:ajax_get_entry_details', kwargs={'pk': self.entry.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['title'], 'AJAX Test Entry')
        self.assertEqual(data['project'], 'Test Project')
        self.assertEqual(len(data['images']), 1)
        self.assertEqual(data['images'][0]['id'], self.image.id)
        self.assertIn('45m', data['duration']) # 1 hour - 15 min pause
        self.assertIn('15m', data['paused_duration'])

    def test_get_time_entry_details_not_found(self):
        url = reverse('tracker:ajax_get_entry_details', kwargs={'pk': 9999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Entry not found.')

    def test_delete_time_entry_image_success(self):
        self.assertEqual(self.entry.images.count(), 1)
        url = reverse('tracker:ajax_delete_image', kwargs={'pk': self.image.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(self.entry.images.count(), 0)

    def test_delete_time_entry_image_not_found(self):
        url = reverse('tracker:ajax_delete_image', kwargs={'pk': 9999})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])

    def test_get_projects_for_category(self):
        Project.objects.create(name='Personal Project', user=self.user, category='personal')
        url = reverse('tracker:ajax_get_projects')
        
        # Test getting 'work' projects
        response_work = self.client.get(url, {'category': 'work'})
        self.assertEqual(response_work.status_code, 200)
        data_work = response_work.json()
        self.assertEqual(len(data_work), 1)
        self.assertEqual(data_work[0]['name'], 'Test Project')

    def test_delete_time_entry_image_get_request(self):
        url = reverse('tracker:ajax_delete_image', kwargs={'pk': self.image.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Invalid request method.')

    def test_get_project_dates_no_project_id(self):
        url = reverse('tracker:ajax_get_project_dates')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'success': False})

    def test_get_project_dates_no_entries(self):
        new_project = Project.objects.create(user=self.user, name='Empty Project')
        url = reverse('tracker:ajax_get_project_dates')
        response = self.client.get(url, {'project_id': new_project.id})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'success': False})


class TerminateAccountViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.url = reverse('tracker:terminate_account_confirm')

    def test_terminate_account_get(self):
        """Test that the confirmation page is rendered on GET."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/terminate_account_confirm.html')
        # Check that the user still exists
        self.assertTrue(get_user_model().objects.filter(id=self.user.id).exists())

    def test_terminate_account_post(self):
        user_id = self.user.id
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('tracker:home'))
        # Check that the user was deleted
        self.assertFalse(get_user_model().objects.filter(id=user_id).exists())

class BulkActionViewsTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.entry1 = TimeEntry.objects.create(
            user=self.user,
            title='Bulk Entry 1',
            start_time=timezone.now() - timedelta(days=3),
            end_time=timezone.now() - timedelta(days=2)
        )
        self.entry2 = TimeEntry.objects.create(
            user=self.user,
            title='Bulk Entry 2',
            start_time=timezone.now() - timedelta(days=2),
            end_time=timezone.now() - timedelta(days=1)
        )
        self.entry3 = TimeEntry.objects.create(
            user=self.user,
            title='Bulk Entry 3',
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now(),
            is_archived=True
        )
        self.delete_confirm_url = reverse('tracker:entry_bulk_delete_confirm')
        self.delete_url = reverse('tracker:entry_bulk_delete')
        self.archive_confirm_url = reverse('tracker:entry_bulk_archive_confirm')
        self.archive_url = reverse('tracker:entry_bulk_archive')
        self.unarchive_confirm_url = reverse('tracker:entry_bulk_unarchive_confirm')

    def test_bulk_delete_confirm_view(self):
        response = self.client.post(self.delete_confirm_url, {'selected_entries': [self.entry1.pk, self.entry2.pk]})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/timeentry_confirm_delete.html')
        self.assertContains(response, 'Bulk Entry 1')
        self.assertContains(response, 'Bulk Entry 2')

    def test_bulk_delete_action(self):
        self.assertEqual(TimeEntry.objects.count(), 3)
        response = self.client.post(self.delete_url, {'selected_entries': [self.entry1.pk, self.entry2.pk]})
        self.assertRedirects(response, reverse('tracker:entry_list'))
        self.assertEqual(TimeEntry.objects.count(), 1)

    def test_bulk_delete_with_preserved_filters(self):
        filters = "category=work&sort_by=date"
        response = self.client.post(self.delete_url, {
            'selected_entries': [self.entry1.pk],
            'preserved_filters': filters
        })
        expected_url = f"{reverse('tracker:entry_list')}?{filters}"
        self.assertRedirects(response, expected_url)

    def test_bulk_delete_get_request(self):
        response = self.client.get(self.delete_url)
        self.assertRedirects(response, reverse('tracker:entry_list'))

    def test_bulk_archive_confirm_view(self):
        response = self.client.post(self.archive_confirm_url, {'selected_entries': [self.entry1.pk]})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/timeentry_confirm_archive.html')
        self.assertContains(response, 'Bulk Entry 1')

    def test_bulk_archive_action(self):
        response = self.client.post(self.archive_url, {'selected_entries': [self.entry1.pk], 'action': 'archive'})
        self.assertRedirects(response, reverse('tracker:entry_list'))
        self.entry1.refresh_from_db()
        self.assertTrue(self.entry1.is_archived)

    def test_bulk_archive_with_preserved_filters(self):
        filters = "show_archived=on"
        response = self.client.post(self.archive_url, {
            'selected_entries': [self.entry1.pk],
            'action': 'archive',
            'preserved_filters': filters
        })
        expected_url = f"{reverse('tracker:entry_list')}?{filters}"
        self.assertRedirects(response, expected_url)

    def test_bulk_archive_get_request(self):
        response = self.client.get(self.archive_url)
        self.assertRedirects(response, reverse('tracker:entry_list'))

    def test_bulk_unarchive_confirm_view(self):
        response = self.client.post(self.unarchive_confirm_url, {'selected_entries': [self.entry3.pk]})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/timeentry_confirm_unarchive.html')
        self.assertContains(response, 'Bulk Entry 3')

    def test_bulk_unarchive_action(self):
        response = self.client.post(self.archive_url, {'selected_entries': [self.entry3.pk], 'action': 'unarchive'})
        self.assertRedirects(response, reverse('tracker:entry_list'))
        self.entry3.refresh_from_db()
        self.assertFalse(self.entry3.is_archived)

    def test_toggle_archive(self):
        toggle_url = reverse('tracker:entry_toggle_archive', kwargs={'pk': self.entry1.pk})
        # This action should be a POST request to be safe
        response = self.client.post(toggle_url)
        self.assertRedirects(response, reverse('tracker:entry_list'))
        self.entry1.refresh_from_db()
        self.assertTrue(self.entry1.is_archived)

    def test_toggle_archive_get_request(self):
        """Test that a GET request to toggle archive redirects without action."""
        toggle_url = reverse('tracker:entry_toggle_archive', kwargs={'pk': self.entry1.pk})
        self.assertFalse(self.entry1.is_archived)
        response = self.client.get(toggle_url)
        self.assertRedirects(response, reverse('tracker:entry_list'))
        self.entry1.refresh_from_db()
        self.assertFalse(self.entry1.is_archived)

class ProjectActionViewsTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.client.login(username='testuser', password='testpassword')
        self.project = Project.objects.create(
            user=self.user,
            name='Cascading Project',
            category='work'
        )
        self.entry1 = TimeEntry.objects.create(
            user=self.user,
            project=self.project,
            title='Entry to archive',
            start_time=timezone.now(),
            end_time=timezone.now()
        )
        self.toggle_archive_url = reverse('tracker:project_toggle_archive', kwargs={'pk': self.project.pk})

    def test_project_archive_and_unarchive_confirm_views(self):
        """Test that the project archive/unarchive confirmation pages load."""
        archive_confirm_url = reverse('tracker:project_archive_confirm', kwargs={'pk': self.project.pk})
        response = self.client.get(archive_confirm_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/project_confirm_archive.html')

        unarchive_confirm_url = reverse('tracker:project_unarchive_confirm', kwargs={'pk': self.project.pk})
        response = self.client.get(unarchive_confirm_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/project_confirm_unarchive.html')

    def test_project_toggle_archive_get_redirects(self):
        """Test that a GET request to the toggle archive URL redirects without action."""
        self.assertFalse(self.project.is_archived)
        response = self.client.get(self.toggle_archive_url)
        self.assertRedirects(response, reverse('tracker:project_list'))
        self.project.refresh_from_db()
        self.assertFalse(self.project.is_archived)

    def test_project_toggle_archive_with_cascade(self):
        self.assertFalse(self.project.is_archived)
        self.assertFalse(self.entry1.is_archived)

        # Archive project and its entries
        response = self.client.post(self.toggle_archive_url, {'archive_entries': 'on'})
        self.assertRedirects(response, reverse('tracker:project_list'))

        self.project.refresh_from_db()
        self.entry1.refresh_from_db()
        self.assertTrue(self.project.is_archived)
        self.assertTrue(self.entry1.is_archived)

    def test_project_toggle_unarchive_with_cascade(self):
        self.project.is_archived = True
        self.project.save()
        self.entry1.is_archived = True
        self.entry1.save()

        # Unarchive project and its entries
        response = self.client.post(self.toggle_archive_url, {'unarchive_entries': 'on'})
        self.assertRedirects(response, reverse('tracker:project_list'))

        self.project.refresh_from_db()
        self.entry1.refresh_from_db()
        self.assertFalse(self.project.is_archived)
        self.assertFalse(self.entry1.is_archived)

    def test_project_toggle_archive_without_cascade(self):
        self.assertFalse(self.project.is_archived)
        self.assertFalse(self.entry1.is_archived)

        # Archive project WITHOUT cascading
        response = self.client.post(self.toggle_archive_url) # No 'archive_entries' in POST data
        self.assertRedirects(response, reverse('tracker:project_list'))

        self.project.refresh_from_db()
        self.entry1.refresh_from_db()
        self.assertTrue(self.project.is_archived)
        self.assertFalse(self.entry1.is_archived) # Entry should NOT be archived

class LoginViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.staff_user = get_user_model().objects.create_user(
            username='staffuser',
            password='testpassword',
            is_staff=True,
        )
        # Grant the staff user permission to view the user list in the admin.
        # This is necessary for the test that checks redirection to an admin page.
        view_user_perm = Permission.objects.get(codename='view_user')
        self.staff_user.user_permissions.add(view_user_perm)

        # The custom login view is not registered under 'account_login' by default
        # in allauth's URL patterns. Since you haven't overridden that URL to point
        # to your custom view, we'll assume it's at a custom path or we can test it directly.
        self.url = reverse('account_login') # This URL points to allauth's default login view.

    def test_regular_user_login_redirects_to_home(self):
        response = self.client.post(
            self.url, {'login': 'testuser', 'password': 'testpassword'}
        )
        self.assertRedirects(response, reverse('tracker:home'))
        # Verify the user is actually logged in
        self.assertTrue(get_user_model().objects.get(username='testuser').is_authenticated)

    def test_staff_user_login_redirects_to_admin(self):
        response = self.client.post(self.url, {'login': 'staffuser', 'password': 'testpassword'})
        # In production environments (DEBUG=False), using reverse('admin:index')
        # can cause issues during startup if the URL patterns aren't fully loaded.
        # The CustomLoginView correctly redirects to the hardcoded '/admin/' path.
        # We test against that hardcoded path for consistency and robustness.
        self.assertRedirects(response, '/admin/')

    def test_staff_user_login_with_next_param(self):
        next_url = reverse('admin:auth_user_changelist')
        login_url_with_next = f"{self.url}?next={next_url}"
        response = self.client.post(
            login_url_with_next, {'login': 'staffuser', 'password': 'testpassword'}
        )
        self.assertRedirects(response, next_url)

    def test_login_failure(self):
        response = self.client.post(self.url, {'login': 'testuser', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'account/login.html')
        self.assertContains(response, 'The username and/or password you specified are not correct.')

class AnalyticsDashboardViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.url = reverse('tracker:analytics')

        # Create projects
        self.work_project = Project.objects.create(user=self.user, name='Work Project', category='work', hourly_rate=Decimal('50.00'))
        self.personal_project = Project.objects.create(user=self.user, name='Personal Project', category='personal')

        # Create time entries
        now = timezone.now()
        TimeEntry.objects.create(user=self.user, project=self.work_project, title='Recent Work', category='work', start_time=now - timedelta(days=2), end_time=now - timedelta(days=2, hours=-1))
        TimeEntry.objects.create(user=self.user, project=self.work_project, title='Old Work', category='work', start_time=now - timedelta(days=40), end_time=now - timedelta(days=40, hours=-2))
        TimeEntry.objects.create(user=self.user, project=self.personal_project, title='Personal Task', category='personal', start_time=now - timedelta(days=5), end_time=now - timedelta(days=5, hours=-1))
        TimeEntry.objects.create(user=self.user, project=None, title='Unassigned Task', category='work', start_time=now - timedelta(days=10), end_time=now - timedelta(days=10, hours=-1))

    def test_dashboard_loads_with_defaults(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/analytics.html')
        # Older task should not be in the default 30d view's earnings calculation
        self.assertNotContains(response, '150.00') # 3 * 50
        # Check for correct earnings calculation (1 hour * 50.00/hr)
        self.assertContains(response, '50.00')

    def test_dashboard_filter_by_period_all(self):
        response = self.client.get(self.url, {'period': 'all'})
        self.assertEqual(response.status_code, 200)
        # Check for correct earnings calculation (1hr + 2hr) * 50.00/hr = 150.00
        self.assertContains(response, '150.00')

    def test_dashboard_filter_by_period_7d(self):
        """Test the dashboard with the 7-day period filter."""
        response = self.client.get(self.url, {'period': '7d'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/analytics.html')
        self.assertIn('activity_chart_datasets', response.context)
        self.assertEqual(response.context['active_period'], '7d')

    def test_dashboard_filter_by_period_1y(self):
        """Test the dashboard with the 1-year period filter."""
        response = self.client.get(self.url, {'period': '1y'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/analytics.html')
        self.assertEqual(response.context['active_period'], '1y')

    def test_dashboard_filter_by_period_3m(self):
        """Test the dashboard with the 3-month period filter."""
        response = self.client.get(self.url, {'period': '3m'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/analytics.html')
        self.assertEqual(response.context['active_period'], '3m')

    def test_dashboard_filter_by_period_15d(self):
        """Test the dashboard with the 15-day period filter."""
        response = self.client.get(self.url, {'period': '15d'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/analytics.html')
        self.assertEqual(response.context['active_period'], '15d')

    def test_dashboard_filter_by_period_6m(self):
        """Test the dashboard with the 6-month period filter."""
        response = self.client.get(self.url, {'period': '6m'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/analytics.html')
        self.assertEqual(response.context['active_period'], '6m')

    def test_dashboard_ajax_filter_by_category(self):
        # This tests the AJAX endpoint that refreshes the activity chart
        response = self.client.get(
            self.url,
            {'period': 'all', 'category': 'work'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('activity_chart_datasets', data)
        project_labels = [d['label'] for d in data['activity_chart_datasets']]
        self.assertIn('Work Project', project_labels)
        self.assertIn('Unassigned', project_labels)
        self.assertNotIn('Personal Project', project_labels)

    def test_dashboard_no_entries(self):
        # Delete all entries and test the empty state
        TimeEntry.objects.all().delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No time tracked yet.')

    def test_dashboard_no_entries_period_all(self):
        """Test the dashboard with period=all when no entries exist."""
        TimeEntry.objects.all().delete()
        response = self.client.get(self.url, {'period': 'all'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No time tracked yet.')
        # Check that the chart data is empty
        self.assertEqual(len(response.context['activity_chart_datasets']), 0)

    def test_dashboard_no_work_or_personal_duration(self):
        TimeEntry.objects.all().delete()
        # Create an entry with a default category that isn't 'work' or 'personal'
        TimeEntry.objects.create(user=self.user, title='No Category', category='other', start_time=timezone.now() - timedelta(hours=1), end_time=timezone.now())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['work_duration'], timedelta(0))
        self.assertEqual(response.context['personal_duration'], timedelta(0))

class CustomSocialAccountAdapterTest(TestCase):
    def setUp(self):
        from .adapters import CustomSocialAccountAdapter
        self.adapter = CustomSocialAccountAdapter()

    def test_pre_social_login_new_user_from_email(self):
        # Mock sociallogin object for a new user
        user = get_user_model()(email='new.user@example.com', first_name='New', last_name='User')
        sociallogin = MagicMock()
        sociallogin.user = user
        sociallogin.account.extra_data = {
            'email': 'new.user@example.com',
            'given_name': 'New',
            'family_name': 'User'
        }

        self.adapter.pre_social_login(request=None, sociallogin=sociallogin)

        # Check that username is generated from email
        self.assertEqual(user.username, 'newuser')
        # Names should be populated
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.last_name, 'User')

    def test_pre_social_login_username_collision(self):
        # Create an existing user with the username that will be generated
        get_user_model().objects.create_user(username='collisionuser', password='password')

        user = get_user_model()(email='collision.user@example.com')
        sociallogin = MagicMock()
        sociallogin.user = user
        sociallogin.account.extra_data = {'email': 'collision.user@example.com'}

        self.adapter.pre_social_login(request=None, sociallogin=sociallogin)

        # Check that the username is made unique
        self.assertEqual(user.username, 'collisionuser1')

    def test_pre_social_login_no_email_fallback_to_name(self):
        user = get_user_model()() # New user, no pk
        sociallogin = MagicMock()
        sociallogin.user = user
        sociallogin.account.extra_data = {
            'given_name': 'FirstName',
            'family_name': 'LastName'
        }

        self.adapter.pre_social_login(request=None, sociallogin=sociallogin)
        self.assertEqual(user.username, 'firstnamelastname')
        self.assertEqual(user.first_name, 'FirstName')
        self.assertEqual(user.last_name, 'LastName')

    def test_pre_social_login_no_user_data(self):
        user = get_user_model()()
        sociallogin = MagicMock()
        sociallogin.user = user
        sociallogin.account.extra_data = {} # No email, no name
        self.adapter.pre_social_login(request=None, sociallogin=sociallogin)
        self.assertEqual(user.username, 'user')

    def test_pre_social_login_existing_user(self):
        # Create an existing user
        existing_user = get_user_model().objects.create_user(
            username='existing',
            password='password',
            first_name='OldFirst',
            last_name='OldLast'
        )
        sociallogin = MagicMock()
        sociallogin.user = existing_user # This user has a pk
        sociallogin.account.extra_data = {} # No extra data

        self.adapter.pre_social_login(request=None, sociallogin=sociallogin)

        # Ensure nothing was changed for the existing user
        self.assertEqual(existing_user.username, 'existing')
        self.assertEqual(existing_user.first_name, 'OldFirst')
        self.assertEqual(existing_user.last_name, 'OldLast')

class ReportAndTranslationViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.project = Project.objects.create(user=self.user, name='Reporting Project', category='work')
        self.entry = TimeEntry.objects.create(
            user=self.user,
            project=self.project,
            title='Report Entry',
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now()
        )
        self.report_url = reverse('tracker:reports')
        self.translate_url = reverse('tracker:translate_report')

    @patch('tracker.views.Translator')
    def test_translate_report_view(self, MockTranslator):
        # Mock the translator instance and its translate method
        mock_translator_instance = MockTranslator.return_value
        mock_translator_instance.translate.side_effect = lambda text, dest: MagicMock(text=f"Translated {text}")

        today = timezone.now().date()
        two_days_ago = today - timedelta(days=2)
        response = self.client.get(self.translate_url, {
            'start_date': two_days_ago.strftime('%Y-%m-%d'),
            'end_date': today.strftime('%Y-%m-%d'),
            'target_language': 'es'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/report_translated.html')
        self.assertContains(response, 'Translated Report Entry')
        # Check that translate was called multiple times (for title, description, notes, static text etc.)
        self.assertTrue(mock_translator_instance.translate.called)

    @patch('tracker.views.Translator')
    def test_translate_report_view_with_project_filter(self, MockTranslator):
        # Mock the translator
        mock_translator_instance = MockTranslator.return_value
        mock_translator_instance.translate.side_effect = lambda text, dest: MagicMock(text=f"Translated {text}")

        # Create another project and entry that should be filtered out
        other_project = Project.objects.create(user=self.user, name='Other Project')
        TimeEntry.objects.create(
            user=self.user,
            project=other_project,
            title='Other Entry',
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now()
        )

        today = timezone.now().date()
        two_days_ago = today - timedelta(days=2)
        response = self.client.get(self.translate_url, {
            'start_date': two_days_ago.strftime('%Y-%m-%d'),
            'end_date': today.strftime('%Y-%m-%d'),
            'target_language': 'es',
            'project': self.project.id # Filter by the main project
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Translated Report Entry')
        self.assertNotContains(response, 'Translated Other Entry')

    def test_report_view_get_initial(self):
        response = self.client.get(self.report_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/report_form.html')
        self.assertIn('form', response.context)
        self.assertIsNone(response.context.get('entries'))

    def test_report_view_csv_export(self):
        today = timezone.now().date()
        two_days_ago = today - timedelta(days=2)
        response = self.client.get(self.report_url, {
            'start_date': two_days_ago.strftime('%Y-%m-%d'),
            'end_date': today.strftime('%Y-%m-%d'),
            'project': self.project.id,
            'export': 'csv',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode('utf-8')
        self.assertIn('Report Entry', content)

    def test_report_view_html_display(self):
        today = timezone.now().date()
        two_days_ago = today - timedelta(days=2)
        response = self.client.get(self.report_url, {
            'start_date': two_days_ago.strftime('%Y-%m-%d'),
            'end_date': today.strftime('%Y-%m-%d'),
            'project': self.project.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/report_form.html')
        self.assertIn('entries', response.context)
        self.assertContains(response, 'Report Entry')
        self.assertIn('total_duration', response.context)

    def test_report_view_filter_by_category(self):
        """Test the report view filtering by category only."""
        # Create an entry in a different category that should be filtered out
        personal_project = Project.objects.create(user=self.user, name='Personal Project', category='personal')
        TimeEntry.objects.create(
            user=self.user,
            project=personal_project,
            title='Personal Entry',
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now()
        )
        
        today = timezone.now().date()
        two_days_ago = today - timedelta(days=2)
        response = self.client.get(self.report_url, {
            'start_date': two_days_ago.strftime('%Y-%m-%d'),
            'end_date': today.strftime('%Y-%m-%d'),
            'category': 'work', # Filter by work category
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Report Entry') # This is in 'work' category
        self.assertNotContains(response, 'Personal Entry')

    @patch('tracker.views.Translator')
    def test_translate_report_csv_export(self, MockTranslator):
        """Test the CSV export functionality of the translated report."""
        mock_translator_instance = MockTranslator.return_value
        mock_translator_instance.translate.side_effect = lambda text, dest: MagicMock(text=f"Translated {text}")

        today = timezone.now().date()
        two_days_ago = today - timedelta(days=2)
        response = self.client.get(self.translate_url, {
            'start_date': two_days_ago.strftime('%Y-%m-%d'),
            'end_date': today.strftime('%Y-%m-%d'),
            'target_language': 'es',
            'export': 'csv'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode('utf-8')
        self.assertIn('Translated Title', content)
        self.assertIn('Translated Report Entry', content)

    def test_report_view_pdf_export(self):
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        response = self.client.get(self.report_url, {'start_date': start_of_month.strftime('%Y-%m-%d'), 'end_date': today.strftime('%Y-%m-%d'), 'export': 'pdf'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF-'))

    @patch('tracker.views.render_to_pdf')
    def test_report_view_pdf_export_error(self, mock_render_to_pdf):
        mock_render_to_pdf.return_value = None # Simulate PDF creation failure
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        response = self.client.get(self.report_url, {'start_date': start_of_month.strftime('%Y-%m-%d'), 'end_date': today.strftime('%Y-%m-%d'), 'export': 'pdf'})
        # Should render the HTML page as a fallback
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/report_form.html')

    @patch('tracker.views.render_to_pdf')
    def test_translate_report_pdf_export(self, mock_render_to_pdf):
        mock_render_to_pdf.return_value = HttpResponse(b'PDF content', content_type='application/pdf')
        today = timezone.now().date()
        two_days_ago = today - timedelta(days=2)
        response = self.client.get(self.translate_url, {
            'start_date': two_days_ago.strftime('%Y-%m-%d'),
            'end_date': today.strftime('%Y-%m-%d'),
            'target_language': 'es',
            'export': 'pdf'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        mock_render_to_pdf.assert_called_once()

    def test_translate_report_view_missing_params(self):
        # Missing 'target_language'
        response = self.client.get(self.translate_url, {
            'start_date': timezone.now().date().strftime('%Y-%m-%d'),
            'end_date': timezone.now().date().strftime('%Y-%m-%d'),
        })
        self.assertRedirects(response, self.report_url)

    @patch('tracker.views.Translator')
    def test_translate_report_view_translator_error(self, MockTranslator):
        mock_translator_instance = MockTranslator.return_value
        # Make the first call (for the language name) fail, and subsequent calls succeed.
        mock_translator_instance.translate.side_effect = [
            TypeError("Translation failed")
        ] + [MagicMock(text=f"Translated {i}") for i in range(30)] # for other fields

        response = self.client.get(self.translate_url, {
            'start_date': (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
            'end_date': timezone.now().date().strftime('%Y-%m-%d'),
            'target_language': 'es'
        })
        self.assertEqual(response.status_code, 200)
        # Because the language name translation failed, it should fall back to the English name.
        self.assertContains(response, 'Spanish')

    @patch('tracker.views.Translator')
    def test_translate_report_with_empty_and_failing_fields(self, MockTranslator):
        # Create an entry with an empty title and a description that will fail translation
        failing_entry = TimeEntry.objects.create(
            user=self.user,
            project=self.project,
            title='', # Empty title
            description='Description to fail',
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now()
        )

        def translate_side_effect(text, dest):
            if text == 'Description to fail':
                raise TypeError("Simulated failure")
            return MagicMock(text=f"Translated {text}")

        mock_translator_instance = MockTranslator.return_value
        mock_translator_instance.translate.side_effect = translate_side_effect

        today = timezone.now().date()
        two_days_ago = today - timedelta(days=2)
        response = self.client.get(self.translate_url, {
            'start_date': two_days_ago.strftime('%Y-%m-%d'),
            'end_date': today.strftime('%Y-%m-%d'),
            'target_language': 'es'
        })
        self.assertEqual(response.status_code, 200)
        # The original description should be used as a fallback
        self.assertContains(response, 'Description to fail')
        
        # Find the specific entry in the context to check its translated title.
        translated_entries = response.context['entries']
        failing_entry_in_context = None
        for entry_dict in translated_entries:
            if entry_dict['original'].pk == failing_entry.pk:
                failing_entry_in_context = entry_dict
                break
        
        self.assertIsNotNone(failing_entry_in_context, "Failing entry not found in response context")
        self.assertEqual(failing_entry_in_context['title'], '', "Translated title for an empty original title should be empty.")

class DailyEarningsTrackerTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.project = Project.objects.create(user=self.user, name='Earnings Project', category='work', hourly_rate=Decimal('100.00'))
        self.entry = TimeEntry.objects.create(
            user=self.user,
            project=self.project,
            title='Earnings Entry',
            start_time=timezone.now() - timedelta(hours=2),
            end_time=timezone.now() - timedelta(hours=1) # 1 hour duration
        )
        self.url = reverse('tracker:daily_earnings_tracker')

    def test_daily_earnings_initial_view(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/daily_earnings_tracker.html')
        self.assertNotIn('gross_pay', response.context)

    def test_daily_earnings_with_data(self):
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        response = self.client.get(self.url, {
            'start_date': start_of_month.strftime('%Y-%m-%d'),
            'end_date': today.strftime('%Y-%m-%d'),
            'project': self.project.id,
            'category': 'work',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('gross_pay', response.context)
        self.assertEqual(response.context['gross_pay'], Decimal('100.00'))
        self.assertContains(response, '100.00 SEK')

    def test_daily_earnings_without_project(self):
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        response = self.client.get(self.url, {
            'start_date': start_of_month.strftime('%Y-%m-%d'),
            'end_date': today.strftime('%Y-%m-%d'),
            'category': 'work',
            # No project ID provided
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('gross_pay', response.context)

class IncomeCalculatorTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.url = reverse('tracker:income_calculator')

    def test_income_calculator_view(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('hourly_rate_to_charge', response.context)
        self.assertTemplateUsed(response, 'tracker/income_calculator.html')

    def test_income_calculator_with_data(self):
        response = self.client.get(self.url, {
            'desired_salary': '40000',
            'overhead_costs': '2000',
            'billable_hours': '140',
            'municipal_tax': '32',
            'profit_margin': '10',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('hourly_rate_to_charge', response.context)
        self.assertGreater(response.context['hourly_rate_to_charge'], 0)
        self.assertContains(response, 'Your Target Hourly Rate')

    def test_income_calculator_invalid_input(self):
        response = self.client.get(self.url, {'desired_salary': 'not-a-number'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid input. Please enter valid numbers.')

class FormTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpassword')
        self.project_work = Project.objects.create(user=self.user, name='Work Form Project', category='work')
        self.project_personal = Project.objects.create(user=self.user, name='Personal Form Project', category='personal')

    def test_time_entry_manual_form_init_with_pause(self):
        from .forms import TimeEntryManualForm
        entry = TimeEntry.objects.create(
            user=self.user,
            title='Paused Entry',
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=2, minutes=30, seconds=15),
            paused_duration=timedelta(hours=1, minutes=5, seconds=10)
        )
        form = TimeEntryManualForm(instance=entry)
        self.assertEqual(form.fields['pause_hours'].initial, 1)
        self.assertEqual(form.fields['pause_minutes'].initial, 5)
        self.assertEqual(form.fields['pause_seconds'].initial, 10)

    def test_time_entry_manual_form_invalid_pause_duration(self):
        from .forms import TimeEntryManualForm
        form_data = {
            'title': 'Invalid Pause',
            'start_time': timezone.now(),
            'end_time': timezone.now() + timedelta(minutes=30),
            'pause_hours': 1, # 1 hour pause on a 30 min entry
            'pause_minutes': 0,
            'pause_seconds': 0,
        }
        form = TimeEntryManualForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Paused duration cannot be greater than the total entry duration.', form.non_field_errors())

    def test_time_entry_manual_form_invalid_end_time(self):
        from .forms import TimeEntryManualForm
        now = timezone.now()
        form_data = {
            'title': 'Invalid End Time',
            'start_time': now,
            'end_time': now - timedelta(minutes=1), # End time before start time
            'category': 'work',
            'project': self.project_work.id,
        }
        form = TimeEntryManualForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('End time must be after start time.', form.non_field_errors())

    def test_time_entry_manual_form_project_category_override(self):
        """Test that the form correctly overrides the category with the project's category."""
        self.project_work.category = 'work'
        self.project_work.save()

        form_data = {
            'title': 'Category Override Test',
            'project': self.project_work.id,
            'category': 'personal',  # Intentionally wrong category
            'start_time': timezone.now(),
            'end_time': timezone.now() + timedelta(hours=1),
        }
        form = TimeEntryManualForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid(), msg=form.errors)
        self.assertEqual(form.cleaned_data['category'], 'work')

    def test_time_entry_manual_form_no_user(self):
        # Test that the form initializes without a user (e.g., in admin)
        form = TimeEntryManualForm()
        # Check that the project queryset is empty, not erroring
        self.assertEqual(form.fields['project'].queryset.count(), 0)

    def test_report_form_dynamic_project_filtering(self):
        from .forms import ReportForm
        # Form with 'work' category should only show work projects
        form_data = {'category': 'work'}
        form = ReportForm(data=form_data, user=self.user)
        project_queryset = form.fields['project'].queryset
        self.assertIn(self.project_work, project_queryset)
        self.assertNotIn(self.project_personal, project_queryset)

    def test_custom_signup_form_save(self):
        from .forms import CustomSignupForm
        form_data = {
            'username': 'newsignup',
            'email': 'newsignup@example.com',
            'password1': 'a-very-secure-pwd-456!',
            'password2': 'a-very-secure-pwd-456!',
            'first_name': 'Custom',
            'last_name': 'Signup',
            'job_title': 'Test Developer',
            'country': 'US',
            'address': '123 Test St',
            'phone_number': '123-456-7890'
        }
        form = CustomSignupForm(form_data)
        # The `msg` argument will print the form's errors if validation fails,
        # which is a clean way to debug form validation issues in tests.
        self.assertTrue(form.is_valid(), msg=form.errors)
        
        # Mock the request object needed by the save method
        mock_request = MagicMock()
        user = form.save(mock_request)

        self.assertIsNotNone(user)
        self.assertEqual(user.first_name, 'Custom')
        self.assertEqual(user.profile.job_title, 'Test Developer')
        self.assertEqual(user.profile.country, 'US')
        self.assertEqual(user.profile.address, '123 Test St')

class MiddlewareTest(TestCase):
    @patch('tracker.middleware.pytz')
    @patch('tracker.middleware.timezone')
    def test_timezone_middleware_valid_cookie(self, mock_timezone, mock_pytz):
        from .middleware import TimezoneMiddleware
        middleware = TimezoneMiddleware(get_response=lambda r: None)
        request = MagicMock()
        request.COOKIES = {'timezone': 'Europe/Stockholm'}

        middleware(request)

        mock_pytz.timezone.assert_called_with('Europe/Stockholm')
        mock_timezone.activate.assert_called_with(mock_pytz.timezone.return_value)

    @patch('tracker.middleware.pytz')
    @patch('tracker.middleware.timezone')
    def test_timezone_middleware_invalid_cookie(self, mock_timezone, mock_pytz):
        from .middleware import TimezoneMiddleware
        import pytz  # Import the real pytz to get the real exception
        middleware = TimezoneMiddleware(get_response=lambda r: None)
        request = MagicMock()
        request.COOKIES = {'timezone': 'Invalid/Timezone'}

        # When the middleware's code runs `except pytz.UnknownTimeZoneError:`,
        # `pytz` is a mock. We need to ensure that `mock_pytz.UnknownTimeZoneError`
        # refers to the actual exception class so it can be caught.
        mock_pytz.UnknownTimeZoneError = pytz.UnknownTimeZoneError
        mock_pytz.timezone.side_effect = pytz.UnknownTimeZoneError

        middleware(request)

        mock_pytz.timezone.assert_called_with('Invalid/Timezone')
        mock_timezone.deactivate.assert_called()
        mock_timezone.activate.assert_not_called()

class ModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='modeltestuser',
            password='password'
        )

    def test_time_entry_duration_for_running_entry(self):
        """Test that the duration property returns None for a running entry."""
        running_entry = TimeEntry.objects.create(
            user=self.user,
            title='Running Entry',
            start_time=timezone.now()
        )
        self.assertIsNone(running_entry.duration)

    def test_time_entry_duration_with_pause(self):
        """Test that the duration property correctly subtracts paused_duration."""
        start = timezone.now()
        end = start + timedelta(hours=1)
        pause = timedelta(minutes=10)
        entry = TimeEntry.objects.create(
            user=self.user,
            title='Paused Duration Test',
            start_time=start,
            end_time=end,
            paused_duration=pause
        )
        expected_duration = timedelta(minutes=50)
        self.assertEqual(entry.duration, expected_duration)

    def test_profile_is_created_for_new_user(self):
        """Test the post_save signal for creating a Profile."""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertIsInstance(self.user.profile, Profile)

    def test_profile_save_signal_on_user_update(self):
        """Test that the user's profile is saved when the user is updated."""
        self.user.first_name = "Updated"
        self.user.save()
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.profile)

    def test_profile_str(self):
        """Test the __str__ method of the Profile model."""
        self.assertEqual(str(self.user.profile), f'{self.user.username} Profile')

    def test_profile_job_title_field(self):
        """Test that the job_title field works correctly."""
        profile = self.user.profile
        profile.job_title = 'Software Engineer'
        profile.save()
        
        profile.refresh_from_db()
        self.assertEqual(profile.job_title, 'Software Engineer')
        
        # Test empty job title
        profile.job_title = ''
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.job_title, '')

    def test_time_entry_str(self):
        """Test the __str__ method of the TimeEntry model."""
        entry = TimeEntry.objects.create(
            user=self.user,
            title='String Test',
            start_time=timezone.now()
        )
        self.assertEqual(str(entry), f'String Test ({self.user.username})')

class ProjectUpdateViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.project = Project.objects.create(user=self.user, name='Original Name')
        self.url = reverse('tracker:project_update', kwargs={'pk': self.project.pk})

    def test_update_view_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/project_form.html')
