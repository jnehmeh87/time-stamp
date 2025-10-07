from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Project, TimeEntry, TimeEntryImage
from users.models import Organization
from django.utils import timezone
from datetime import timedelta
from urllib.parse import urlencode
from PIL import Image
from django.core.files import File
import os

User = get_user_model()

class ProjectListViewTest(TestCase):
    def setUp(self):
        # Create a test user that we can log in with
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.organization = Organization.objects.create(name='Test Organization')
        self.organization.members.add(self.user)
        # Create a test project associated with the user
        self.project = Project.objects.create(
            name='Test Work Project',
            description='A test project for work.',
            category='work',
            organization=self.organization
        )

    def test_project_list_view_requires_login(self):
        """
        Test that the project list page redirects if the user is not logged in.
        """
        # The URL name 'tracker:project_list' is based on your template paths.
        # If your URL is named differently, you may need to adjust this.
        url = reverse('workspaces:project_list')
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

        url = reverse('workspaces:project_list')
        response = self.client.get(url)

        # Check that the page loads successfully (status code 200).
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'workspaces/project_list.html')

    def test_project_is_displayed_on_list_page(self):
        """
        Test that a created project's name is visible on the project list page.
        """
        self.client.login(username='testuser', password='testpassword')
        url = reverse('workspaces:project_list')
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
        self.organization = Organization.objects.create(name='Test Organization')
        self.organization.members.add(self.user)
        # Log the user in for all tests in this class
        self.client.login(username='testuser', password='testpassword')
        self.url = reverse('workspaces:project_create')

    def test_create_project_page_loads(self):
        """Test that the project creation page loads correctly."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'workspaces/project_form.html')

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
        self.assertRedirects(response, reverse('workspaces:project_list'))

        # Check that the project was actually created in the database
        self.assertTrue(Project.objects.filter(name='New Test Project').exists())

    def test_delete_project_view(self):
        """Test that a project can be deleted."""
        project_to_delete = Project.objects.create(
            organization=self.organization, name='Will be deleted'
        )
        delete_url = reverse('workspaces:project_delete', kwargs={'pk': project_to_delete.pk})
        self.assertTrue(Project.objects.filter(pk=project_to_delete.pk).exists())
        response = self.client.post(delete_url)
        self.assertRedirects(response, reverse('workspaces:project_list'))
        self.assertFalse(Project.objects.filter(pk=project_to_delete.pk).exists())

    def test_delete_project_get_confirm_page(self):
        """Test that the project delete confirmation page loads."""
        project_to_delete = Project.objects.create(organization=self.organization, name='Confirm Delete')
        delete_url = reverse('workspaces:project_delete', kwargs={'pk': project_to_delete.pk})
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'workspaces/project_confirm_delete.html')

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
        self.url = reverse('workspaces:entry_update', kwargs={'pk': self.entry.pk})

    def test_update_view_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'workspaces/timeentry_update_form.html')

    def test_update_entry_successfully(self):
        form_data = {
            'title': 'Updated Title',
            'project': self.project.id,
            'category': 'work',
            'start_time': self.entry.start_time.strftime('%Y-%m-%dT%H:%M'),
            'end_time': self.entry.end_time.strftime('%Y-%m-%dT%H:%M'),
        }
        response = self.client.post(self.url, data=form_data)
        self.assertRedirects(response, reverse('workspaces:entry_list'))
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
        self.assertRedirects(response, reverse('workspaces:entry_list'))
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

        self.assertRedirects(response, reverse('workspaces:entry_list'))
        self.assertEqual(self.entry.images.count(), 1)

        # Clean up the test image
        os.remove(image_path)

class TimeEntryCreateViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.url = reverse('workspaces:entry_create')

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

        self.assertRedirects(response, reverse('workspaces:entry_list'))
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
        self.url = reverse('workspaces:entry_delete', kwargs={'pk': self.entry.pk})

    def test_delete_view_get_request(self):
        """Test that a GET request to the delete view shows the confirmation page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'workspaces/timeentry_confirm_delete.html')
        self.assertContains(response, 'Are you sure you want to delete')

    def test_delete_view_post_request(self):
        """Test that a POST request deletes the entry."""
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('workspaces:entry_list'))
        self.assertFalse(TimeEntry.objects.filter(pk=self.entry.pk).exists())

class TimeEntryListViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.organization = Organization.objects.create(name='Test Organization')
        self.organization.members.add(self.user)
        self.client.login(username='testuser', password='testpassword')
        self.project = Project.objects.create(
            name='Test Project',
            organization=self.organization,
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
        self.url = reverse('workspaces:entry_list')

    def test_list_view_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'workspaces/timeentry_list.html')

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
        self.delete_confirm_url = reverse('workspaces:entry_bulk_delete_confirm')
        self.delete_url = reverse('workspaces:entry_bulk_delete')
        self.archive_confirm_url = reverse('workspaces:entry_bulk_archive_confirm')
        self.archive_url = reverse('workspaces:entry_bulk_archive')
        self.unarchive_confirm_url = reverse('workspaces:entry_bulk_unarchive_confirm')

    def test_bulk_delete_confirm_view(self):
        response = self.client.post(self.delete_confirm_url, {'selected_entries': [self.entry1.pk, self.entry2.pk]})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'workspaces/timeentry_confirm_delete.html')
        self.assertContains(response, 'Bulk Entry 1')
        self.assertContains(response, 'Bulk Entry 2')

    def test_bulk_delete_action(self):
        self.assertEqual(TimeEntry.objects.count(), 3)
        response = self.client.post(self.delete_url, {'selected_entries': [self.entry1.pk, self.entry2.pk]})
        self.assertRedirects(response, reverse('workspaces:entry_list'))
        self.assertEqual(TimeEntry.objects.count(), 1)

    def test_bulk_delete_with_preserved_filters(self):
        filters = "category=work&sort_by=date"
        response = self.client.post(self.delete_url, {
            'selected_entries': [self.entry1.pk],
            'preserved_filters': filters
        })
        expected_url = f"{reverse('workspaces:entry_list')}?{filters}"
        self.assertRedirects(response, expected_url)

    def test_bulk_delete_get_request(self):
        response = self.client.get(self.delete_url)
        self.assertRedirects(response, reverse('workspaces:entry_list'))

    def test_bulk_archive_confirm_view(self):
        response = self.client.post(self.archive_confirm_url, {'selected_entries': [self.entry1.pk]})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'workspaces/timeentry_confirm_archive.html')
        self.assertContains(response, 'Bulk Entry 1')

    def test_bulk_archive_action(self):
        response = self.client.post(self.archive_url, {'selected_entries': [self.entry1.pk], 'action': 'archive'})
        self.assertRedirects(response, reverse('workspaces:entry_list'))
        self.entry1.refresh_from_db()
        self.assertTrue(self.entry1.is_archived)

    def test_bulk_archive_with_preserved_filters(self):
        filters = "show_archived=on"
        response = self.client.post(self.archive_url, {
            'selected_entries': [self.entry1.pk],
            'action': 'archive',
            'preserved_filters': filters
        })
        expected_url = f"{reverse('workspaces:entry_list')}?{filters}"
        self.assertRedirects(response, expected_url)

    def test_bulk_archive_get_request(self):
        response = self.client.get(self.archive_url)
        self.assertRedirects(response, reverse('workspaces:entry_list'))

    def test_bulk_unarchive_confirm_view(self):
        response = self.client.post(self.unarchive_confirm_url, {'selected_entries': [self.entry3.pk]})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'workspaces/timeentry_confirm_unarchive.html')
        self.assertContains(response, 'Bulk Entry 3')

    def test_bulk_unarchive_action(self):
        response = self.client.post(self.archive_url, {'selected_entries': [self.entry3.pk], 'action': 'unarchive'})
        self.assertRedirects(response, reverse('workspaces:entry_list'))
        self.entry3.refresh_from_db()
        self.assertFalse(self.entry3.is_archived)

    def test_toggle_archive(self):
        toggle_url = reverse('workspaces:entry_toggle_archive', kwargs={'pk': self.entry1.pk})
        # This action should be a POST request to be safe
        response = self.client.post(toggle_url)
        self.assertRedirects(response, reverse('workspaces:entry_list'))
        self.entry1.refresh_from_db()
        self.assertTrue(self.entry1.is_archived)

    def test_toggle_archive_get_request(self):
        """Test that a GET request to toggle archive redirects without action."""
        toggle_url = reverse('workspaces:entry_toggle_archive', kwargs={'pk': self.entry1.pk})
        self.assertFalse(self.entry1.is_archived)
        response = self.client.get(toggle_url)
        self.assertRedirects(response, reverse('workspaces:entry_list'))
        self.entry1.refresh_from_db()
        self.assertFalse(self.entry1.is_archived)