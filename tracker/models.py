from django.db import models
from django.conf import settings
from datetime import timedelta

CATEGORY_CHOICES = [
    ('work', 'Work'),
    ('personal', 'Personal'),
]

class Project(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='work')
    is_archived = models.BooleanField(default=False)

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

class TimeEntryImage(models.Model):
    time_entry = models.ForeignKey(TimeEntry, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='time_entry_images/')

    def __str__(self):
        return f"Image for {self.time_entry.title}"
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
        return f"Image for {self.time_entry.title}"
