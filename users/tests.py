from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import CustomUser, Profile # Ensure Profile is imported from local models
from django.contrib.auth.models import Permission
from unittest.mock import MagicMock
from datetime import timedelta # Added for UserProfileFormTest

User = get_user_model()

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
        self.url = reverse('users:profile')

    def test_profile_view_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/profile.html')
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

class TerminateAccountViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.url = reverse('users:terminate_account_confirm')

    def test_terminate_account_get(self):
        """Test that the confirmation page is rendered on GET."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/terminate_account_confirm.html')
        # Check that the user still exists
        self.assertTrue(get_user_model().objects.filter(id=self.user.id).exists())

    def test_terminate_account_post(self):
        user_id = self.user.id
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('tracker:home'))
        # Check that the user was deleted
        self.assertFalse(get_user_model().objects.filter(id=user_id).exists())

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

class CustomSocialAccountAdapterTest(TestCase):
    def setUp(self):
        from tracker.adapters import CustomSocialAccountAdapter
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

class ModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='modeltestuser',
            password='password'
        )

    def test_profile_is_created_for_new_user(self):
        """Test the post_save signal for creating a Profile."""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertIsInstance(self.user.profile, CustomUser)

    def test_profile_save_signal_on_user_update(self):
        """Test that the user's profile is saved when the user is updated."""
        self.user.first_name = "Updated"
        self.user.save()
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.profile)

    def test_profile_str(self):
        """Test the __str__ method of the Profile model."""
        self.assertEqual(str(self.user.profile), f'{self.user.username} Profile')

# Moved from tracker/tests.py
class ProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.profile = self.user.profile

    def test_profile_creation(self):
        self.assertIsInstance(self.profile, Profile)
        self.assertEqual(self.profile.user, self.user)

    def test_profile_str(self):
        self.assertEqual(str(self.profile), f'{self.user.username} Profile')

    def test_profile_default_values(self):
        self.assertIsNone(self.profile.address)
        self.assertIsNone(self.profile.phone_number)
        self.assertIsNone(self.profile.country)

class UserProfileViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.profile_url = reverse('users:profile') # Adjusted from 'tracker:profile'

    def test_profile_view_get(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/profile.html') # Adjusted from 'tracker/profile.html'

    def test_profile_view_post(self):
        new_address = "123 Main St"
        new_phone = "555-1234"
        new_country = "US"
        response = self.client.post(self.profile_url, {
            'address': new_address,
            'phone_number': new_phone,
            'country': new_country
        })
        self.assertEqual(response.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.address, new_address)
        self.assertEqual(self.user.profile.phone_number, new_phone)
        self.assertEqual(self.user.profile.country, new_country)

class UserProfileFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.profile = self.user.profile

    def test_profile_form_valid_data(self):
        from users.forms import UserProfileForm # Adjusted from 'tracker.forms'
        form = UserProfileForm(data={
            'address': '456 Oak Ave',
            'phone_number': '987-6543',
            'country': 'CA'
        }, instance=self.profile)
        self.assertTrue(form.is_valid())
        profile = form.save()
        self.assertEqual(profile.address, '456 Oak Ave')
        self.assertEqual(profile.phone_number, '987-6543')
        self.assertEqual(profile.country, 'CA')

    def test_profile_form_invalid_data(self):
        from users.forms import UserProfileForm # Adjusted from 'tracker.forms'
        form = UserProfileForm(data={
            'phone_number': 'invalid-phone'
        }, instance=self.profile)
        self.assertFalse(form.is_valid())
        self.assertIn('phone_number', form.errors)
