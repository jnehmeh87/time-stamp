from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from datetime import timedelta

class Project(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    CATEGORY_CHOICES = [
        ('work', 'Work'),
        ('personal', 'Personal'),
    ]
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='work')

    class Meta:
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        indexes = [
            models.Index(fields=['user', 'name']),
        ]

    def __str__(self):
        return self.name

class TimeEntry(models.Model):
    CATEGORY_CHOICES = [
        ('work', 'Work'),
        ('personal', 'Personal'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='time_entries')
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True, help_text="Description of what you achieved.")
    notes = models.TextField(blank=True, help_text="Notes for the next session.")
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='work')
    is_archived = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)
    # Fields for pause/resume functionality
    is_paused = models.BooleanField(default=False)
    paused_duration = models.DurationField(default=timedelta(0))
    last_pause_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['user', 'start_time']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['is_archived', 'is_hidden']),
        ]

    def __str__(self):
        return f"{self.title} ({self.user.username})"

    def clean(self):
        if self.end_time and self.end_time < self.start_time:
            raise ValidationError("End time cannot be earlier than start time.")

    @property
    def duration(self):
        if self.end_time:
            total_duration = self.end_time - self.start_time
            return total_duration - self.paused_duration
        return None

    def formatted_duration(self):
        d = self.duration
        if not d:
            return ""
        total = int(d.total_seconds())
        h, rem = divmod(total, 3600)
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
