from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Project, TimeEntry, Profile, TimeEntryImage
from django.utils import timezone
from PIL import Image
from django.core.files import File
import os
from django.http import QueryDict
from django.template import Context, Template
from datetime import timedelta
from unittest.mock import patch, MagicMock
from decimal import Decimal, InvalidOperation
from .utils import format_duration_hms

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
                'project': self.project.id,
                'category': 'work',
                'start_time': self.entry.start_time.strftime('%Y-%m-%dT%H:%M'),
                'end_time': self.entry.end_time.strftime('%Y-%m-%dT%H:%M'),
                'description': 'Test description with image.',
                'notes': 'Test notes with image.',
                'pause_hours': 0,
                'pause_minutes': 10,
                'pause_seconds': 0,
            }
            response = self.client.post(self.url, data={**form_data, 'images': f})

        self.assertRedirects(response, reverse('tracker:entry_list'))
        self.assertEqual(self.entry.images.count(), 1)

        # Clean up the test image
        os.remove(image_path)

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

    def test_profile_view_post_success(self):
        form_data = {
            'first_name': 'UpdatedFirst',
            'last_name': 'UpdatedLast',
            'email': 'updated@example.com',
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

class TerminateAccountViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.url = reverse('tracker:terminate_account_confirm')

    def test_terminate_account_post(self):
        user_id = self.user.id
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('tracker:home'))
        # Check that the user was deleted
        self.assertFalse(get_user_model().objects.filter(id=user_id).exists())

class BulkActionViewsTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpassword'
        )
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
        response = self.client.get(toggle_url)
        self.assertRedirects(response, reverse('tracker:entry_list'))
        self.entry1.refresh_from_db()
        self.assertTrue(self.entry1.is_archived)

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
        start_of_month = today.replace(day=1)
        response = self.client.get(self.translate_url, {
            'start_date': start_of_month.strftime('%Y-%m-%d'),
            'end_date': today.strftime('%Y-%m-%d'),
            'target_language': 'es'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/report_translated.html')
        self.assertContains(response, 'Translated Report Entry')
        # Check that translate was called multiple times (for title, description, notes, static text etc.)
        self.assertTrue(mock_translator_instance.translate.called)

    def test_report_view_get_initial(self):
        response = self.client.get(self.report_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/report_form.html')
        self.assertIn('form', response.context)
        self.assertIsNone(response.context.get('entries'))

    def test_report_view_csv_export(self):
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        response = self.client.get(self.report_url, {
            'start_date': start_of_month.strftime('%Y-%m-%d'),
            'end_date': today.strftime('%Y-%m-%d'),
            'project': self.project.id,
            'export': 'csv',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode('utf-8')
        self.assertIn('Report Entry', content)

    @patch('tracker.views.render_to_pdf')
    def test_report_view_pdf_export(self, mock_render_to_pdf):
        from django.http import HttpResponse
        mock_render_to_pdf.return_value = HttpResponse(b'PDF content', content_type='application/pdf')
        
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        response = self.client.get(self.report_url, {'start_date': start_of_month, 'end_date': today, 'export': 'pdf'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        mock_render_to_pdf.assert_called_once()
        self.assertEqual(mock_render_to_pdf.call_args[0][0], 'tracker/report_untranslated_pdf.html')

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

class IncomeCalculatorTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.url = reverse('tracker:income_calculator')

    def test_income_calculator_view(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
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
            'password': 'a-very-secure-pwd-456!',
            'password2': 'a-very-secure-pwd-456!',
            'first_name': 'Custom',
            'last_name': 'Signup',
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