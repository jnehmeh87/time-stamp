from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_countries.fields import CountryField
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta

CATEGORY_CHOICES = [
    ('work', 'Work'),
    ('personal', 'Personal'),
]

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    country = CountryField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f'{self.user.username} Profile'

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Create a profile for new users, or save the profile for existing users.
    """
    if created:
        Profile.objects.create(user=instance)
    # Ensure the profile is saved when the user is saved.
    instance.profile.save()


class Project(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='work')
    is_archived = models.BooleanField(default=False)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    def __str__(self):
        return self.name

class TimeEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='time_entries')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='work')
    is_paused = models.BooleanField(default=False)
    last_pause_time = models.DateTimeField(null=True, blank=True)
    paused_duration = models.DurationField(default=timedelta(0))
    is_manual = models.BooleanField(default=False)  # Add this field
    was_edited = models.BooleanField(default=False) # Add this line

    class Meta:
        ordering = ['-start_time']

    @property
    def duration(self):
        if self.end_time:
            # Ensure paused_duration is not None before subtracting
            paused_time = self.paused_duration or timedelta(0)
            return self.end_time - self.start_time - paused_time
        return None
    
    def __str__(self):
        return f"{self.title} ({self.user.username})"

    def save(self, *args, **kwargs):
        if self.project:
            self.category = self.project.category
        super().save(*args, **kwargs)

class TimeEntryImage(models.Model):
    time_entry = models.ForeignKey(TimeEntry, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='time_entry_images/')

    def __str__(self):
        return f"Image for {self.time_entry.title}"
        return f"Image for {self.time_entry.title}"
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

class TimeEntryImage(models.Model):
    time_entry = models.ForeignKey(TimeEntry, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='time_entry_images/')

    class Meta:
        indexes = [
            models.Index(fields=['time_entry']),
        ]

    def __str__(self):
        return f"Image for {self.time_entry.title}"
        return f"Image for {self.time_entry.title}"
