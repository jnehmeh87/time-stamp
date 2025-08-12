from django.db import models
from django.conf import settings

class Project(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

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

    def __str__(self):
        return f"{self.title} ({self.user.username})"

    @property
    def duration(self):
        if self.end_time:
            return self.end_time - self.start_time
        return None

class TimeEntryImage(models.Model):
    time_entry = models.ForeignKey(TimeEntry, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='time_entry_images/')

    def __str__(self):
        return f"Image for {self.time_entry.title}"
